"""Shipment domain services: CRUD, order assignment and cost pools."""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.enums import ShipmentStatus
from app.domain.models import Order, Shipment, ShipmentCost
from app.domain.schemas import ShipmentIn


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

    shipment.costs.clear()
    for cost in payload.costs:
        shipment.costs.append(
            ShipmentCost(
                type=cost.type,
                amount_eur_cents=cost.amount_eur_cents,
                method=cost.method,
            )
        )

    _apply_orders(db, shipment, payload.order_ids)


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
