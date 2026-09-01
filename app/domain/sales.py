"""Sales and listings: record sales with a landed-cost snapshot."""
from __future__ import annotations

import json

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.domain.costs import compute_order_landed
from app.domain.enums import ListingStatus, MovementKind
from app.domain.inventory import InventoryError, current_lot_unit_cost, lot_to_dict
from app.domain.models import (
    Bundle,
    BundleItem,
    BundleListing,
    InventoryLot,
    Listing,
    LotMovement,
    Order,
    Sale,
    Shipment,
)


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
    bundle_id: str | None = None,
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
        bundle_id=bundle_id,
    )
    db.add(sale)
    db.commit()
    db.refresh(sale)
    return sale


def create_listing(
    db: Session, lot: InventoryLot, quantity: int, unit_price_eur_cents: int,
    marketplace: str = "OTHER",
) -> Listing:
    if quantity <= 0 or quantity > lot.available:
        raise InventoryError("Cantidad inválida")
    marketplace = (marketplace or "OTHER").strip().upper()
    duplicate = db.scalar(
        select(Listing).where(
            Listing.lot_id == lot.id,
            Listing.marketplace == marketplace,
            Listing.status == ListingStatus.ACTIVE,
        )
    )
    if duplicate is not None:
        raise InventoryError("Ya existe un anuncio activo en ese marketplace")
    listing = Listing(
        lot_id=lot.id, quantity=quantity,
        unit_price_eur_cents=unit_price_eur_cents, marketplace=marketplace,
    )
    db.add(listing)
    db.commit()
    db.refresh(listing)
    return listing


def update_listing(
    db: Session, listing: Listing, quantity: int, unit_price_eur_cents: int,
    marketplace: str,
) -> Listing:
    if listing.status not in (ListingStatus.ACTIVE, ListingStatus.NEEDS_REMOVAL):
        raise InventoryError("Solo se pueden editar anuncios activos o pendientes de ajustar")
    if quantity <= 0 or quantity > listing.lot.available:
        raise InventoryError(f"Cantidad inválida (1..{listing.lot.available})")
    marketplace = (marketplace or "OTHER").strip().upper()
    duplicate = db.scalar(
        select(Listing).where(
            Listing.lot_id == listing.lot_id,
            Listing.marketplace == marketplace,
            Listing.status == ListingStatus.ACTIVE,
            Listing.id != listing.id,
        )
    )
    if duplicate is not None:
        raise InventoryError("Ya existe un anuncio activo en ese marketplace")
    listing.quantity = quantity
    listing.unit_price_eur_cents = unit_price_eur_cents
    listing.marketplace = marketplace
    listing.status = ListingStatus.ACTIVE
    db.commit()
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
    for other in db.scalars(
        select(Listing).where(
            Listing.lot_id == listing.lot_id,
            Listing.id != listing.id,
            Listing.status == ListingStatus.ACTIVE,
        )
    ):
        if other.quantity > listing.lot.available:
            other.status = ListingStatus.NEEDS_REMOVAL
    _flag_unavailable_bundles(db, listing.lot_id)
    db.commit()
    return sale


def update_sale(
    db: Session,
    sale: Sale,
    quantity: int,
    unit_price_eur_cents: int,
    fees_eur_cents: int = 0,
) -> Sale:
    if quantity <= 0:
        raise InventoryError("La cantidad debe ser mayor que cero")
    if unit_price_eur_cents < 0 or fees_eur_cents < 0:
        raise InventoryError("El precio y las comisiones no pueden ser negativos")
    difference = quantity - sale.quantity
    if difference > sale.lot.available:
        raise InventoryError(f"Solo quedan {sale.lot.available} unidades disponibles")
    if difference:
        sale.lot.available -= difference
        sale.lot.movements.append(LotMovement(
            kind=MovementKind.SALE_ADJUSTMENT,
            delta=-difference,
        ))
    sale.quantity = quantity
    sale.unit_price_eur_cents = unit_price_eur_cents
    sale.fees_eur_cents = fees_eur_cents
    if difference > 0:
        for individual in sale.lot.listings:
            if individual.status == ListingStatus.ACTIVE and individual.quantity > sale.lot.available:
                individual.status = ListingStatus.NEEDS_REMOVAL
        _flag_unavailable_bundles(db, sale.lot_id)
    db.commit()
    return sale


def delete_sale(db: Session, sale: Sale) -> None:
    """Delete a sale transaction and restore its stock with an audit movement."""
    sales = [sale]
    if sale.bundle_id:
        sales = list(db.scalars(select(Sale).where(Sale.bundle_id == sale.bundle_id)))
    for row in sales:
        row.lot.available += row.quantity
        row.lot.movements.append(
            LotMovement(kind=MovementKind.SALE_ADJUSTMENT, delta=row.quantity)
        )
        db.delete(row)
    db.commit()


def _flag_unavailable_bundles(db: Session, lot_id: str) -> None:
    bundle_ids = list(db.scalars(select(BundleItem.bundle_id).where(BundleItem.lot_id == lot_id)))
    if not bundle_ids:
        return
    for bundle in db.scalars(
        select(Bundle).options(selectinload(Bundle.items).selectinload(BundleItem.lot))
        .where(Bundle.id.in_(bundle_ids))
    ):
        if any(item.lot.available < item.quantity for item in bundle.items):
            for listing in bundle.listings:
                if listing.status == ListingStatus.ACTIVE:
                    listing.status = ListingStatus.NEEDS_REMOVAL


def create_bundle(db: Session, name: str, items_data, listings_data) -> Bundle:
    name = name.strip()
    if not name:
        raise InventoryError("Indica un nombre para el bundle")
    if len(items_data) < 2:
        raise InventoryError("Un bundle necesita al menos dos cartas")
    bundle = Bundle(name=name)
    seen = set()
    for data in items_data:
        if data.lot_id in seen:
            raise InventoryError("No repitas el mismo lote; aumenta su cantidad")
        seen.add(data.lot_id)
        lot = db.get(InventoryLot, data.lot_id)
        if lot is None or data.quantity <= 0 or data.quantity > lot.available:
            raise InventoryError("Cantidad de bundle no disponible")
        bundle.items.append(BundleItem(lot=lot, quantity=data.quantity))
    if not listings_data:
        raise InventoryError("Selecciona al menos un marketplace")
    for data in listings_data:
        bundle.listings.append(BundleListing(
            marketplace=(data.marketplace or "OTHER").strip().upper(),
            unit_price_eur_cents=data.unit_price_eur_cents,
        ))
    db.add(bundle)
    db.commit()
    return bundle


def sell_bundle_listing(
    db: Session, listing: BundleListing, unit_price_eur_cents: int,
    fees_eur_cents: int = 0,
) -> Bundle:
    if listing.status != ListingStatus.ACTIVE:
        raise InventoryError("El bundle no está activo")
    bundle = listing.bundle
    if any(item.lot.available < item.quantity for item in bundle.items):
        raise InventoryError("No hay stock suficiente para completar el bundle")
    costs = [(current_lot_unit_cost(item.lot) or 0) * item.quantity for item in bundle.items]
    total_cost = sum(costs)
    weights = costs if total_cost else [item.quantity for item in bundle.items]
    total_weight = sum(weights) or 1
    assigned = 0
    for pos, item in enumerate(bundle.items):
        revenue = unit_price_eur_cents - assigned if pos == len(bundle.items) - 1 else round(unit_price_eur_cents * weights[pos] / total_weight)
        assigned += revenue
        sell_lot(db, item.lot, item.quantity, round(revenue / item.quantity), fees_eur_cents if pos == 0 else 0, bundle_id=bundle.id)
        for individual in item.lot.listings:
            if individual.status == ListingStatus.ACTIVE and individual.quantity > item.lot.available:
                individual.status = ListingStatus.NEEDS_REMOVAL
    listing.status = ListingStatus.SOLD
    for other in bundle.listings:
        if other.id != listing.id and other.status == ListingStatus.ACTIVE:
            other.status = ListingStatus.NEEDS_REMOVAL
    db.commit()
    return bundle


def bundle_to_dict(bundle: Bundle) -> dict:
    items = []
    max_available = None
    total_cost = 0
    for item in bundle.items:
        info = lot_to_dict(item.lot)
        possible = item.lot.available // item.quantity
        max_available = possible if max_available is None else min(max_available, possible)
        unit_cost = info["unit_cost_eur_cents"] or 0
        total_cost += unit_cost * item.quantity
        items.append({
            "lot_id": item.lot_id, "quantity": item.quantity,
            "available": item.lot.available, "name": info["name"],
            "name_en": info["name_en"], "set_code": info["set_code"],
            "collector_number": info["collector_number"], "image_path": info["image_path"],
            "unit_cost_eur_cents": info["unit_cost_eur_cents"],
        })
    return {
        "id": bundle.id, "name": bundle.name, "created_at": bundle.created_at,
        "total_cost_eur_cents": total_cost, "max_available": max_available or 0,
        "items": items,
        "listings": [{"id": row.id, "marketplace": row.marketplace,
                      "unit_price_eur_cents": row.unit_price_eur_cents,
                      "status": row.status} for row in bundle.listings],
    }


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
        "name_en": info["name_en"],
        "set_code": info["set_code"],
        "collector_number": info["collector_number"],
        "revenue_eur_cents": revenue,
        "cost_eur_cents": cost,
        "profit_eur_cents": profit,
        "roi_pct": roi,
        "card_id": info["card_id"],
        "image_path": info["image_path"],
        "bundle_id": sale.bundle_id,
        "bundle_name": sale.bundle.name if sale.bundle else None,
        "bundle_image_paths": [
            lot_to_dict(item.lot)["image_path"]
            for item in sale.bundle.items
            if lot_to_dict(item.lot)["image_path"]
        ] if sale.bundle else [],
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
        "name_en": info["name_en"],
        "set_code": info["set_code"],
        "collector_number": info["collector_number"],
        "image_path": info["image_path"],
        "available": listing.lot.available,
        "marketplace": listing.marketplace,
        "purchase_cost_eur_cents": info["unit_cost_eur_cents"],
        "card_id": info["card_id"],
    }
