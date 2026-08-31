"""Shipment and cost-category endpoints."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.db import get_db
from app.domain.inventory import receive_shipment
from app.domain.models import CostCategory, Order, OrderItem, Shipment, ShipmentCost
from app.domain.schemas import (
    CostCategoryIn,
    CostCategoryOut,
    ShipmentIn,
    ShipmentOut,
)
from app.domain.shipments import (
    ShipmentError,
    create_category,
    create_shipment,
    list_categories,
    load_shipment,
    shipment_to_dict,
    update_shipment,
)

router = APIRouter(prefix="/shipments", tags=["shipments"])
categories_router = APIRouter(prefix="/cost-categories", tags=["cost-categories"])


def _load(shipment_id: str, db: Session) -> Shipment:
    shipment = load_shipment(db, shipment_id)
    if shipment is None:
        raise HTTPException(status_code=404, detail="Envío no encontrado")
    return shipment


@router.post("", response_model=ShipmentOut, status_code=201)
def create(payload: ShipmentIn, db: Session = Depends(get_db)) -> dict:
    try:
        shipment = create_shipment(db, payload)
    except ShipmentError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return shipment_to_dict(_load(shipment.id, db))


@router.get("", response_model=list[ShipmentOut])
def list_shipments(db: Session = Depends(get_db)) -> list[dict]:
    shipments = list(
        db.scalars(
            select(Shipment)
            .options(
                selectinload(Shipment.costs).selectinload(ShipmentCost.category),
                selectinload(Shipment.orders).selectinload(Order.items).selectinload(OrderItem.card),
            )
            .order_by(Shipment.created_at.desc())
        )
    )
    return [shipment_to_dict(shipment) for shipment in shipments]


@router.get("/{shipment_id}", response_model=ShipmentOut)
def get_shipment(shipment_id: str, db: Session = Depends(get_db)) -> dict:
    return shipment_to_dict(_load(shipment_id, db))


@router.put("/{shipment_id}", response_model=ShipmentOut)
def update_shipment_endpoint(
    shipment_id: str, payload: ShipmentIn, db: Session = Depends(get_db)
) -> dict:
    shipment = _load(shipment_id, db)
    try:
        update_shipment(db, shipment, payload)
    except ShipmentError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return shipment_to_dict(_load(shipment_id, db))


@router.post("/{shipment_id}/receive", response_model=ShipmentOut)
def receive(shipment_id: str, db: Session = Depends(get_db)) -> dict:
    shipment = _load(shipment_id, db)
    receive_shipment(db, shipment)
    return shipment_to_dict(_load(shipment_id, db))


@categories_router.get("", response_model=list[CostCategoryOut])
def list_categories_endpoint(db: Session = Depends(get_db)) -> list[CostCategory]:
    return list_categories(db)


@categories_router.post("", response_model=CostCategoryOut, status_code=201)
def create_category_endpoint(
    payload: CostCategoryIn, db: Session = Depends(get_db)
) -> CostCategory:
    try:
        return create_category(db, payload.name, payload.kind)
    except ShipmentError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
