"""Overview aggregation: invested, inventory value, sales and ROI."""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.domain.costs import compute_order_landed
from app.domain.models import (
    InventoryLot,
    Order,
    OrderItem,
    Sale,
    Shipment,
)


def compute_overview(db: Session) -> dict:
    orders = list(db.scalars(select(Order).options(selectinload(Order.items))))
    shipments = {
        shipment.id: shipment
        for shipment in db.scalars(
            select(Shipment).options(
                selectinload(Shipment.costs),
                selectinload(Shipment.orders).selectinload(Order.items),
            )
        )
    }

    invested = sum(round(order.total_paid_fen * order.fx_cny_eur) for order in orders)

    lots = list(
        db.scalars(
            select(InventoryLot)
            .options(selectinload(InventoryLot.order_item).selectinload(OrderItem.order))
            .order_by(InventoryLot.created_at)
        )
    )

    landed_cache: dict[str, dict] = {}
    inventory_units = 0
    inventory_value = 0
    for lot in lots:
        if lot.available <= 0:
            continue
        if lot.order_item is None:
            unit = lot.unit_cost_eur_cents or 0
            invested += unit * lot.quantity
        else:
            order = lot.order_item.order
            if order.id not in landed_cache:
                landed_cache[order.id] = compute_order_landed(
                    order, shipments.get(order.shipment_id)
                )
            entry = next(
                (e for e in landed_cache[order.id]["items"] if e["item_id"] == lot.order_item.id),
                None,
            )
            unit = round(entry["landed_eur_cents"] / entry["quantity"]) if entry and entry["quantity"] else 0
        inventory_units += lot.available
        inventory_value += lot.available * unit

    sales = list(db.scalars(select(Sale)))
    revenue = sum(sale.quantity * sale.unit_price_eur_cents for sale in sales)
    cost = sum(
        sale.quantity * sale.landed_unit_eur_cents + sale.fees_eur_cents for sale in sales
    )
    profit = revenue - cost
    roi = round(profit / cost * 100, 1) if cost else 0.0

    return {
        "orders_count": len(orders),
        "invested_eur_cents": invested,
        "inventory_units": inventory_units,
        "inventory_value_eur_cents": inventory_value,
        "sold_units": sum(sale.quantity for sale in sales),
        "revenue_eur_cents": revenue,
        "cost_eur_cents": cost,
        "profit_eur_cents": profit,
        "roi_pct": roi,
    }
