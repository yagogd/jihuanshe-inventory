"""Shipment domain services: CRUD, order assignment and cost breakdown.

The shipment total is paid in EUR and is the source of truth for landed cost.
The breakdown lines may be in EUR or CNY (the warehouse quotes in yuan); their
EUR equivalents must add up to the total before the shipment can be saved.
"""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.domain.costs import shipment_cost_eur_cents
from app.domain.enums import CostCategoryKind, Currency, ShipmentStatus
from app.domain.models import CostCategory, Order, Shipment, ShipmentCost
from app.domain.schemas import OrderOut, ShipmentIn


class ShipmentError(ValueError):
    pass


def total_eur_cents(costs: list[ShipmentCost], fx_cny_eur: float) -> int:
    return sum(shipment_cost_eur_cents(cost, fx_cny_eur) for cost in costs)


def fit_fx(total_paid_eur_cents: int, costs: list[ShipmentCost]) -> float | None:
    """Return the FX that makes the CNY lines cover the remainder of the total.

    ``None`` when there are no CNY lines (nothing to fit).
    """
    eur_lines = sum(c.amount for c in costs if c.currency == Currency.EUR)
    cny_fen = sum(c.amount for c in costs if c.currency == Currency.CNY)
    if cny_fen <= 0:
        return None
    return (total_paid_eur_cents - eur_lines) / cny_fen


def create_shipment(db: Session, payload: ShipmentIn) -> Shipment:
    shipment = Shipment(status=payload.status or ShipmentStatus.PREPARING)
    db.add(shipment)
    db.flush()
    _apply(db, shipment, payload)
    db.commit()
    return shipment


def update_shipment(db: Session, shipment: Shipment, payload: ShipmentIn) -> Shipment:
    _apply(db, shipment, payload)
    db.commit()
    return shipment


def _apply(db: Session, shipment: Shipment, payload: ShipmentIn) -> None:
    if payload.status is not None:
        shipment.status = payload.status

    shipment.total_paid_eur_cents = payload.total_paid_eur_cents
    if payload.fx_source:
        shipment.fx_source = payload.fx_source
    if payload.fx_cny_eur is not None:
        shipment.fx_cny_eur = payload.fx_cny_eur

    shipment.costs.clear()
    for position, cost in enumerate(payload.costs):
        shipment.costs.append(
            ShipmentCost(
                category_id=cost.category_id,
                amount=cost.amount,
                currency=cost.currency,
                method=cost.method,
                insured_amount=cost.insured_amount,
                insured_currency=cost.insured_currency,
                position=position,
            )
        )

    _validate(shipment)
    _apply_orders(db, shipment, payload.order_ids)


def _validate(shipment: Shipment) -> None:
    total = total_eur_cents(shipment.costs, shipment.fx_cny_eur)
    if total != shipment.total_paid_eur_cents:
        raise ShipmentError(
            f"El desglose suma {total / 100:.2f} € pero el total del envío es "
            f"{shipment.total_paid_eur_cents / 100:.2f} €"
        )


def _apply_orders(db: Session, shipment: Shipment, order_ids: list[str]) -> None:
    desired = set(order_ids)
    current = {
        oid for (oid,) in db.execute(select(Order.id).where(Order.shipment_id == shipment.id))
    }
    for oid in current - desired:
        order = db.get(Order, oid)
        if order is not None:
            order.shipment = None
    for oid in desired - current:
        order = db.get(Order, oid)
        if order is not None:
            order.shipment = shipment


def load_shipment(db: Session, shipment_id: str) -> Shipment | None:
    return db.scalar(
        select(Shipment)
        .options(
            selectinload(Shipment.costs).selectinload(ShipmentCost.category),
            selectinload(Shipment.orders).selectinload(Order.items),
        )
        .where(Shipment.id == shipment_id)
    )


def shipment_to_dict(shipment: Shipment) -> dict:
    return {
        "id": shipment.id,
        "status": shipment.status,
        "total_paid_eur_cents": shipment.total_paid_eur_cents,
        "fx_cny_eur": shipment.fx_cny_eur,
        "fx_source": shipment.fx_source,
        "created_at": shipment.created_at,
        "costs": [
            {
                "id": cost.id,
                "category_id": cost.category_id,
                "category_name": cost.category.name if cost.category else "",
                "category_kind": cost.category.kind.value
                if cost.category and cost.category.kind
                else "",
                "amount": cost.amount,
                "currency": cost.currency,
                "method": cost.method,
                "insured_amount": cost.insured_amount,
                "insured_currency": cost.insured_currency,
                "amount_eur_cents": shipment_cost_eur_cents(cost, shipment.fx_cny_eur),
            }
            for cost in shipment.costs
        ],
        "orders": [OrderOut.model_validate(order).model_dump() for order in shipment.orders],
        "has_sales": shipment.has_sales,
    }


def list_categories(db: Session) -> list[CostCategory]:
    return list(
        db.scalars(select(CostCategory).order_by(CostCategory.position, CostCategory.name))
    )


def create_category(db: Session, name: str, kind: str) -> CostCategory:
    name = name.strip()
    if not name:
        raise ShipmentError("El nombre de la categoría no puede estar vacío")
    existing = db.scalar(select(CostCategory).where(CostCategory.name == name))
    if existing is not None:
        return existing
    try:
        kind_value = CostCategoryKind(kind)
    except ValueError:
        kind_value = CostCategoryKind.CUSTOM
    category = CostCategory(name=name, kind=kind_value)
    db.add(category)
    db.commit()
    db.refresh(category)
    return category
