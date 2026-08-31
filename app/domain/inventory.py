"""Inventory domain services: materialize lots, move units, split and add.

Lots now link to a catalog Card directly (``card_id``). Lots created from a
received shipment keep an optional ``order_item_id`` for audit; manual lots
(European purchases, etc.) have no order item.
"""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.domain.cards import resolve_card
from app.domain.enums import LotSource, MovementKind, ShipmentStatus
from app.domain.fx import convert_to_eur
from app.domain.models import InventoryLot, LotMovement, OrderItem, Shipment
from app.domain.schemas import InventoryLotIn

_MANUAL_KINDS = {MovementKind.SELL, MovementKind.GRADE}


class InventoryError(ValueError):
    pass


def receive_shipment(db: Session, shipment: Shipment) -> list[InventoryLot]:
    """Mark a shipment RECEIVED and materialize one lot per order item.

    Idempotent: items that already have a lot are skipped.
    """
    shipment.status = ShipmentStatus.RECEIVED
    created: list[InventoryLot] = []
    for order in shipment.orders:
        for item in order.items:
            existing = db.scalar(
                select(InventoryLot).where(InventoryLot.order_item_id == item.id)
            )
            if existing is not None:
                continue
            lot = InventoryLot(
                order_item_id=item.id,
                card_id=item.card_id,
                source=LotSource.RECEIVE,
                quantity=item.quantity,
                available=item.quantity,
            )
            lot.movements.append(
                LotMovement(kind=MovementKind.RECEIVE, delta=item.quantity)
            )
            db.add(lot)
            created.append(lot)
    db.commit()
    return created


def add_manual_lot(db: Session, payload: InventoryLotIn) -> InventoryLot:
    card = resolve_card(
        db,
        game=payload.game,
        set_code=payload.set_code,
        collector_number=payload.collector_number,
        raw_name=payload.name_zh,
        name_en=payload.name_en,
        language=payload.language,
        variant=payload.variant,
        foil=payload.foil,
        promo=payload.promo,
        image_path=payload.image_path,
    )
    if card is None:
        raise InventoryError("Se necesita set y número para identificar la carta")

    quantity = payload.quantity if payload.quantity > 0 else 1
    total_eur = convert_to_eur(payload.amount, payload.currency.value, db)
    unit_cost = round(total_eur / quantity) if quantity else 0

    lot = InventoryLot(
        card_id=card.id,
        source=LotSource.MANUAL,
        quantity=quantity,
        available=quantity,
        amount=payload.amount,
        currency=payload.currency,
        unit_cost_eur_cents=unit_cost,
        note=payload.note,
        image_path=payload.image_path,
    )
    lot.movements.append(LotMovement(kind=MovementKind.RECEIVE, delta=quantity))
    db.add(lot)
    db.commit()
    db.refresh(lot)
    return lot


def split_lot(db: Session, lot: InventoryLot, quantity: int) -> InventoryLot:
    if quantity <= 0 or quantity >= lot.available:
        raise InventoryError(
            f"Cantidad inválida para dividir (1..{lot.available - 1})"
        )

    lot.available -= quantity
    lot.movements.append(LotMovement(kind=MovementKind.SPLIT_OUT, delta=-quantity))

    new_lot = InventoryLot(
        order_item_id=lot.order_item_id,
        card_id=lot.card_id,
        source=lot.source,
        quantity=quantity,
        available=quantity,
        unit_cost_eur_cents=lot.unit_cost_eur_cents,
        note=lot.note,
        image_path=lot.image_path,
    )
    new_lot.movements.append(LotMovement(kind=MovementKind.SPLIT_IN, delta=quantity))
    db.add(new_lot)
    db.commit()
    db.refresh(new_lot)
    return new_lot


def add_movement(db: Session, lot: InventoryLot, kind: MovementKind, quantity: int) -> LotMovement:
    if kind not in _MANUAL_KINDS:
        raise InventoryError("Solo se permiten movimientos SELL o GRADE")
    if quantity <= 0 or quantity > lot.available:
        raise InventoryError(
            f"Cantidad inválida (1..{lot.available})"
        )

    lot.available -= quantity
    movement = LotMovement(kind=kind, delta=-quantity)
    lot.movements.append(movement)
    db.commit()
    db.refresh(movement)
    return movement


def lot_to_dict(lot: InventoryLot) -> dict:
    card = lot.card
    item = lot.order_item

    name = card.name_zh if card and card.name_zh else None
    if not name and item:
        name = item.normalized_name or item.raw_name
    name_en = card.name_en if card else None
    raw_name = card.name_zh if card and card.name_zh else (item.raw_name if item else None)

    image_path = None
    if card and card.image_path:
        image_path = card.image_path
    elif lot.image_path:
        image_path = lot.image_path
    elif item:
        image_path = item.image_path

    order_id = seller = purchase_date = None
    if item is not None and item.order is not None:
        order_id = item.order.id
        seller = item.order.seller
        purchase_date = item.order.purchase_date

    return {
        "id": lot.id,
        "order_item_id": lot.order_item_id,
        "card_id": lot.card_id,
        "source": lot.source.value if lot.source else LotSource.RECEIVE.value,
        "name": name or "(sin nombre)",
        "name_en": name_en,
        "raw_name": raw_name,
        "game": card.game if card else (item.game if item else None),
        "set_code": card.set_code if card else (item.set_code if item else None),
        "collector_number": (
            card.collector_number if card else (item.collector_number if item else None)
        ),
        "condition": item.condition if item else None,
        "variant": card.variant if card else (item.variant if item else None),
        "language": card.language if card else (item.language if item else None),
        "foil": card.foil if card else (item.foil if item else False),
        "promo": card.promo if card else (item.promo if item else False),
        "origin": item.origin.value if item and item.origin else None,
        "image_path": image_path,
        "quantity": lot.quantity,
        "available": lot.available,
        "unit_cost_eur_cents": lot.unit_cost_eur_cents,
        "note": lot.note,
        "order_id": order_id,
        "seller": seller,
        "purchase_date": purchase_date,
    }


def pending_item_to_dict(item: OrderItem) -> dict:
    """Represent an order line that has not been received yet as an inventory row."""
    card = item.card
    name_zh = (
        card.name_zh if card and card.name_zh else (item.normalized_name or item.raw_name)
    )
    name_en = card.name_en if card else None
    fx = item.order.fx_cny_eur if item.order else 0.13

    return {
        "id": item.id,
        "order_item_id": item.id,
        "card_id": item.card_id,
        "source": "PENDING",
        "name": name_zh or "(sin nombre)",
        "name_en": name_en,
        "raw_name": item.raw_name,
        "game": card.game if card else item.game,
        "set_code": card.set_code if card else item.set_code,
        "collector_number": card.collector_number if card else item.collector_number,
        "condition": item.condition,
        "variant": card.variant if card else item.variant,
        "language": card.language if card else item.language,
        "foil": card.foil if card else item.foil,
        "promo": card.promo if card else item.promo,
        "origin": item.origin.value if item.origin else None,
        "image_path": (card.image_path if card and card.image_path else item.image_path),
        "quantity": item.quantity,
        "available": 0,
        "unit_cost_eur_cents": round(item.unit_price_fen * fx),
        "note": None,
        "order_id": item.order.id if item.order else None,
        "seller": item.order.seller if item.order else None,
        "purchase_date": item.order.purchase_date if item.order else None,
    }


def list_inventory_entries(db: Session) -> list[dict]:
    """Return every card in inventory: received lots, manual lots and pending orders."""
    lots = list(
        db.scalars(
            select(InventoryLot)
            .options(
                selectinload(InventoryLot.order_item).selectinload(OrderItem.order),
                selectinload(InventoryLot.card),
            )
        )
    )
    entries = [lot_to_dict(lot) for lot in lots]

    received_item_ids = {lot.order_item_id for lot in lots if lot.order_item_id}
    items = list(
        db.scalars(
            select(OrderItem)
            .options(selectinload(OrderItem.order), selectinload(OrderItem.card))
            .order_by(OrderItem.position)
        )
    )
    for item in items:
        if item.id in received_item_ids:
            continue
        entries.append(pending_item_to_dict(item))

    return entries
