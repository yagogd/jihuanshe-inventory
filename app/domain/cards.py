"""Card catalog services: resolve identity and keep names translated.

A card is identified by ``(game, set_code, collector_number)``. The Chinese
name is stored as scraped; the English name is filled once (see
``app.domain.translate``) and never overwritten by later imports.
"""
from __future__ import annotations

import re
from collections import defaultdict

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.domain.costs import compute_order_landed
from app.domain.models import (
    Card,
    InventoryLot,
    Listing,
    Order,
    OrderItem,
    Sale,
    Shipment,
    ShipmentCost,
)


def card_identity(
    game: str | None, set_code: str | None, collector_number: str | None
) -> tuple[str, str, str] | None:
    """Return the (game, set, number) key, or ``None`` when identity is incomplete.

    A card without set and number cannot be catalogued: the caller keeps the
    purchase unlinked instead of inventing an identity.
    """
    set_code = (set_code or "").strip()
    number = (collector_number or "").strip()
    if not set_code and number:
        combined = re.fullmatch(r"([A-Za-z0-9]+)-(.+?/\d+)", number)
        if combined:
            set_code, number = combined.groups()
    if not set_code or not number:
        return None
    return ((game or "").strip(), set_code, number)


def resolve_card(
    db: Session,
    *,
    game: str | None,
    set_code: str | None,
    collector_number: str | None,
    raw_name: str | None = None,
    name_en: str | None = None,
    language: str | None = None,
    variant: str | None = None,
    foil: bool = False,
    promo: bool = False,
    image_path: str | None = None,
) -> Card | None:
    """Get-or-create the Card for an identity, filling missing attributes.

    Existing attributes are left untouched; a card already has a Chinese name
    and a translation, so re-importing the same card is a no-op on names.
    """
    identity = card_identity(game, set_code, collector_number)
    if identity is None:
        return None
    card_game, card_set, card_number = identity

    card = db.scalar(
        select(Card).where(
            Card.game == card_game,
            Card.set_code == card_set,
            Card.collector_number == card_number,
        )
    )
    if card is None:
        card = Card(game=card_game or None, set_code=card_set, collector_number=card_number)
        db.add(card)
        db.flush()

    if not card.name_zh and raw_name:
        card.name_zh = raw_name
    if name_en and not card.name_en:
        card.name_en = name_en
    if language and not card.language:
        card.language = language
    if variant and not card.variant:
        card.variant = variant
    card.foil = card.foil or foil
    card.promo = card.promo or promo
    if image_path and not card.image_path:
        card.image_path = image_path
    return card


def backfill_cards(db: Session) -> int:
    """Link existing order items to catalog Cards; create them when missing.

    Returns the number of items linked. Items without set/number are skipped.
    """
    items = list(
        db.scalars(
            select(OrderItem).where(OrderItem.card_id.is_(None)).order_by(OrderItem.position)
        )
    )
    linked = 0
    for item in items:
        card = resolve_card(
            db,
            game=item.game,
            set_code=item.set_code,
            collector_number=item.collector_number,
            raw_name=item.raw_name,
            language=item.language,
            variant=item.variant,
            foil=item.foil,
            promo=item.promo,
            image_path=item.image_path,
        )
        if card is not None:
            item.card_id = card.id
            item.set_code = card.set_code
            item.collector_number = card.collector_number
            linked += 1
    if linked:
        db.commit()
    return linked


_SORT_KEYS = {
    "name_en": lambda c: (c["name_en"] or c["name_zh"] or "").lower(),
    "name_zh": lambda c: (c["name_zh"] or "").lower(),
    "set_code": lambda c: (c["set_code"] or "").lower(),
    "collector_number": lambda c: (c["collector_number"] or "").lower(),
    "game": lambda c: (c["game"] or "").lower(),
    "stock_qty": lambda c: c["stock_qty"],
    "avg_price": lambda c: c["avg_price_eur_cents"] if c["avg_price_eur_cents"] is not None else -1,
}


def _card_aggregates(db: Session) -> tuple[dict[str, int], dict[str, int], dict[str, int]]:
    """Return (stock, purchased_qty, purchased_value) keyed by card id."""
    stock: dict[str, int] = defaultdict(int)
    purchased_qty: dict[str, int] = defaultdict(int)
    purchased_value: dict[str, int] = defaultdict(int)

    lots = db.scalars(select(InventoryLot).options(selectinload(InventoryLot.order_item)))
    for lot in lots:
        card_id = lot.card_id or (lot.order_item.card_id if lot.order_item else None)
        if card_id:
            stock[card_id] += lot.available

    items = db.scalars(select(OrderItem).options(selectinload(OrderItem.order)))
    for item in items:
        if item.card_id is None:
            continue
        purchased_qty[item.card_id] += item.quantity
        fx = item.order.fx_cny_eur if item.order else 0.13
        purchased_value[item.card_id] += round(item.unit_price_fen * item.quantity * fx)

    return stock, purchased_qty, purchased_value


def card_to_dict(card: Card, stock: int, qty: int, value: int) -> dict:
    return {
        "id": card.id,
        "game": card.game,
        "set_code": card.set_code,
        "collector_number": card.collector_number,
        "name_zh": card.name_zh,
        "name_en": card.name_en,
        "language": card.language,
        "variant": card.variant,
        "foil": card.foil,
        "promo": card.promo,
        "image_path": card.image_path,
        "stock_qty": stock,
        "total_qty": qty,
        "avg_price_eur_cents": round(value / qty) if qty else None,
    }


def list_cards(
    db: Session,
    q: str | None = None,
    sort: str = "name_en",
    order: str = "asc",
) -> list[dict]:
    stock, purchased_qty, purchased_value = _card_aggregates(db)

    result = []
    needle = (q or "").strip().lower()
    for card in db.scalars(select(Card)):
        data = card_to_dict(
            card,
            stock.get(card.id, 0),
            purchased_qty.get(card.id, 0),
            purchased_value.get(card.id, 0),
        )
        if needle:
            haystack = " ".join(
                str(data[k] or "")
                for k in ("name_en", "name_zh", "set_code", "collector_number", "game")
            ).lower()
            if needle not in haystack:
                continue
        result.append(data)

    key = _SORT_KEYS.get(sort, _SORT_KEYS["name_en"])
    result.sort(key=key, reverse=order == "desc")
    return result


def card_detail(db: Session, card: Card) -> dict:
    stock, purchased_qty, purchased_value = _card_aggregates(db)
    data = card_to_dict(
        card,
        stock.get(card.id, 0),
        purchased_qty.get(card.id, 0),
        purchased_value.get(card.id, 0),
    )

    purchases = []
    for item in db.scalars(
        select(OrderItem)
        .options(selectinload(OrderItem.order))
        .where(OrderItem.card_id == card.id)
        .order_by(OrderItem.position)
    ):
        order = item.order
        shipment = None
        if order and order.shipment_id:
            shipment = db.scalar(
                select(Shipment)
                .options(
                    selectinload(Shipment.costs).selectinload(ShipmentCost.category),
                    selectinload(Shipment.orders).selectinload(Order.items),
                )
                .where(Shipment.id == order.shipment_id)
            )
        landed_item = None
        if order:
            landed = compute_order_landed(order, shipment)
            landed_item = next(
                (row for row in landed["items"] if row["item_id"] == item.id), None
            )
        purchases.append(
            {
                "id": item.id,
                "order_id": item.order.id if item.order else "",
                "seller": item.order.seller if item.order else None,
                "purchase_date": item.order.purchase_date if item.order else None,
                "quantity": item.quantity,
                "unit_price_fen": item.unit_price_fen,
                "fx_cny_eur": item.order.fx_cny_eur if item.order else 0.13,
                "condition": item.condition,
                "image_path": item.image_path,
                "order_name": order.display_name if order else None,
                "order_status": order.status.value if order and order.status else None,
                "express_company": order.express_company if order else None,
                "express_tracking": order.express_tracking if order else None,
                "shipment_id": order.shipment_id if order else None,
                "purchase_cny_fen": landed_item["purchase_cny_fen"] if landed_item else 0,
                "domestic_cny_fen": landed_item["domestic_cny_fen"] if landed_item else 0,
                "alipay_cny_fen": landed_item["alipay_cny_fen"] if landed_item else 0,
                "cny_eur_cents": landed_item["cny_eur_cents"] if landed_item else 0,
                "shipment_alloc_cents": landed_item["shipment_alloc_cents"] if landed_item else {},
                "shipment_eur_cents": landed_item["shipment_eur_cents"] if landed_item else 0,
                "landed_eur_cents": landed_item["landed_eur_cents"] if landed_item else 0,
                "unit_landed_eur_cents": round(
                    landed_item["landed_eur_cents"] / item.quantity
                ) if landed_item and item.quantity else 0,
                "allocation_method": order.cost_method if order else "BY_VALUE",
                "shipment_allocation_method": (
                    shipment.cost_method if shipment else "BY_VALUE"
                ),
                "inventory_excluded": item.excluded_from_inventory,
            }
        )

    lots = []
    for lot in db.scalars(
        select(InventoryLot)
        .options(selectinload(InventoryLot.order_item))
        .where(InventoryLot.card_id == card.id)
    ):
        lots.append(
            {
                "id": lot.id,
                "quantity": lot.quantity,
                "available": lot.available,
                "unit_cost_eur_cents": lot.unit_cost_eur_cents,
                "condition": lot.order_item.condition if lot.order_item else None,
                "image_path": lot.image_path
                or (lot.order_item.image_path if lot.order_item else None),
                "order_item_id": lot.order_item_id,
            }
        )

    data["purchases"] = purchases
    data["lots"] = lots
    lot_ids = [lot.id for lot in db.scalars(select(InventoryLot).where(InventoryLot.card_id == card.id))]
    data["listings"] = [
        {
            "id": listing.id, "lot_id": listing.lot_id, "card_id": card.id,
            "quantity": listing.quantity,
            "unit_price_eur_cents": listing.unit_price_eur_cents,
            "purchase_cost_eur_cents": listing.lot.unit_cost_eur_cents,
            "marketplace": listing.marketplace, "status": listing.status,
            "created_at": listing.created_at, "name": data["name_zh"] or "(sin nombre)",
            "name_en": data["name_en"], "set_code": data["set_code"],
            "collector_number": data["collector_number"], "image_path": data["image_path"],
            "available": listing.lot.available,
        }
        for listing in db.scalars(
            select(Listing).options(selectinload(Listing.lot))
            .where(Listing.lot_id.in_(lot_ids)).order_by(Listing.created_at.desc())
        )
    ] if lot_ids else []
    data["sales"] = []
    if lot_ids:
        for sale in db.scalars(
            select(Sale).options(selectinload(Sale.lot))
            .where(Sale.lot_id.in_(lot_ids)).order_by(Sale.sold_at.desc())
        ):
            revenue = sale.quantity * sale.unit_price_eur_cents
            cost = sale.quantity * sale.landed_unit_eur_cents + sale.fees_eur_cents
            profit = revenue - cost
            data["sales"].append({
                "id": sale.id, "lot_id": sale.lot_id, "card_id": card.id,
                "quantity": sale.quantity, "unit_price_eur_cents": sale.unit_price_eur_cents,
                "fees_eur_cents": sale.fees_eur_cents,
                "landed_unit_eur_cents": sale.landed_unit_eur_cents,
                "sold_at": sale.sold_at, "name": data["name_zh"] or "(sin nombre)",
                "name_en": data["name_en"], "set_code": data["set_code"],
                "collector_number": data["collector_number"], "revenue_eur_cents": revenue,
                "cost_eur_cents": cost, "profit_eur_cents": profit,
                "roi_pct": round(profit / cost * 100, 1) if cost else 0.0,
            })
    return data


def rename_card(db: Session, card: Card, name_en: str | None) -> Card:
    if name_en is not None:
        card.name_en = name_en.strip() or None
    db.commit()
    db.refresh(card)
    return card
