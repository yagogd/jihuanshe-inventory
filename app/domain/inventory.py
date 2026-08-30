"""Inventory domain services: materialize lots, move units, split lots."""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.enums import MovementKind, ShipmentStatus
from app.domain.models import InventoryLot, LotMovement, Shipment

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
                order_item_id=item.id, quantity=item.quantity, available=item.quantity
            )
            lot.movements.append(
                LotMovement(kind=MovementKind.RECEIVE, delta=item.quantity)
            )
            db.add(lot)
            created.append(lot)
    db.commit()
    return created


def split_lot(db: Session, lot: InventoryLot, quantity: int) -> InventoryLot:
    if quantity <= 0 or quantity >= lot.available:
        raise InventoryError(
            f"Cantidad inválida para dividir (1..{lot.available - 1})"
        )

    lot.available -= quantity
    lot.movements.append(LotMovement(kind=MovementKind.SPLIT_OUT, delta=-quantity))

    new_lot = InventoryLot(
        order_item_id=lot.order_item_id,
        quantity=quantity,
        available=quantity,
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
    item = lot.order_item
    order = item.order
    return {
        "id": lot.id,
        "order_item_id": lot.order_item_id,
        "name": item.normalized_name or item.raw_name,
        "raw_name": item.raw_name,
        "game": item.game,
        "set_code": item.set_code,
        "collector_number": item.collector_number,
        "condition": item.condition,
        "variant": item.variant,
        "language": item.language,
        "image_path": item.image_path,
        "quantity": lot.quantity,
        "available": lot.available,
        "order_id": order.id,
        "seller": order.seller,
        "purchase_date": order.purchase_date,
    }
