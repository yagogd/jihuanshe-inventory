"""Sales and listings: record sales with a landed-cost snapshot."""
from __future__ import annotations

import json

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.domain.costs import compute_order_landed
from app.domain.enums import ListingStatus, MovementKind
from app.domain.inventory import InventoryError, lot_to_dict
from app.domain.models import InventoryLot, Listing, LotMovement, Order, Sale, Shipment


def _snapshot(db: Session, lot: InventoryLot) -> tuple[int, str]:
    if lot.order_item is None:
        return lot.unit_cost_eur_cents or 0, "{}"
    item = lot.order_item
    order = item.order
    shipment = None
    if order.shipment_id:
        shipment = db.scalar(
            select(Shipment)
            .options(
                selectinload(Shipment.costs),
                selectinload(Shipment.orders).selectinload(Order.items),
            )
            .where(Shipment.id == order.shipment_id)
        )
    landed = compute_order_landed(order, shipment)
    entry = next((e for e in landed["items"] if e["item_id"] == item.id), None)
    unit = round(entry["landed_eur_cents"] / item.quantity) if entry and item.quantity else 0
    return unit, json.dumps(entry, ensure_ascii=False) if entry else "{}"


def sell_lot(
    db: Session,
    lot: InventoryLot,
    quantity: int,
    unit_price_eur_cents: int,
    fees_eur_cents: int = 0,
) -> Sale:
    if quantity <= 0 or quantity > lot.available:
        raise InventoryError(f"Cantidad inválida (1..{lot.available})")
    unit_landed, snapshot = _snapshot(db, lot)

    lot.available -= quantity
    lot.movements.append(LotMovement(kind=MovementKind.SELL, delta=-quantity))

    sale = Sale(
        lot_id=lot.id,
        quantity=quantity,
        unit_price_eur_cents=unit_price_eur_cents,
        fees_eur_cents=fees_eur_cents,
        landed_unit_eur_cents=unit_landed,
        landed_snapshot_json=snapshot,
    )
    db.add(sale)
    db.commit()
    db.refresh(sale)
    return sale


def create_listing(
    db: Session, lot: InventoryLot, quantity: int, unit_price_eur_cents: int
) -> Listing:
    if quantity <= 0:
        raise InventoryError("Cantidad inválida")
    listing = Listing(
        lot_id=lot.id, quantity=quantity, unit_price_eur_cents=unit_price_eur_cents
    )
    db.add(listing)
    db.commit()
    db.refresh(listing)
    return listing


def sell_listing(
    db: Session,
    listing: Listing,
    quantity: int,
    unit_price_eur_cents: int,
    fees_eur_cents: int = 0,
) -> Sale:
    if listing.status != ListingStatus.ACTIVE:
        raise InventoryError("El listado no está activo")
    if quantity <= 0 or quantity > listing.quantity:
        raise InventoryError(f"Cantidad inválida (1..{listing.quantity})")

    sale = sell_lot(db, listing.lot, quantity, unit_price_eur_cents, fees_eur_cents)

    listing.quantity -= quantity
    if listing.quantity <= 0:
        listing.status = ListingStatus.SOLD
    db.commit()
    return sale


def remove_listing(db: Session, listing: Listing) -> Listing:
    listing.status = ListingStatus.REMOVED
    db.commit()
    return listing


def sale_to_dict(sale: Sale) -> dict:
    revenue = sale.quantity * sale.unit_price_eur_cents
    cost = sale.quantity * sale.landed_unit_eur_cents + sale.fees_eur_cents
    profit = revenue - cost
    roi = round(profit / cost * 100, 1) if cost else 0.0
    info = lot_to_dict(sale.lot)
    return {
        "id": sale.id,
        "lot_id": sale.lot_id,
        "quantity": sale.quantity,
        "unit_price_eur_cents": sale.unit_price_eur_cents,
        "fees_eur_cents": sale.fees_eur_cents,
        "landed_unit_eur_cents": sale.landed_unit_eur_cents,
        "sold_at": sale.sold_at,
        "name": info["name"],
        "set_code": info["set_code"],
        "collector_number": info["collector_number"],
        "revenue_eur_cents": revenue,
        "cost_eur_cents": cost,
        "profit_eur_cents": profit,
        "roi_pct": roi,
    }


def listing_to_dict(listing: Listing) -> dict:
    info = lot_to_dict(listing.lot)
    return {
        "id": listing.id,
        "lot_id": listing.lot_id,
        "quantity": listing.quantity,
        "unit_price_eur_cents": listing.unit_price_eur_cents,
        "status": listing.status,
        "created_at": listing.created_at,
        "name": info["name"],
        "set_code": info["set_code"],
        "collector_number": info["collector_number"],
        "image_path": info["image_path"],
        "available": listing.lot.available,
    }
