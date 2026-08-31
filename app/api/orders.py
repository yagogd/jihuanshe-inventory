"""Order endpoints."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.db import get_db
from app.domain.costs import compute_order_landed
from app.domain.enums import OrderStatus
from app.domain.models import Order, OrderItem, Shipment
from app.domain.orders import OrderEditError, persist_order
from app.domain.orders import update_order as update_order_data
from app.domain.schemas import LandedOut, OrderIn, OrderOut, OrderStatusIn

router = APIRouter(prefix="/orders", tags=["orders"])

_ORDER_LOAD = selectinload(Order.items).selectinload(OrderItem.card)


@router.post("", response_model=OrderOut, status_code=201)
def create_order(payload: OrderIn, db: Session = Depends(get_db)) -> Order:
    if payload.jihuanshe_order_id:
        existing = db.scalar(
            select(Order).where(Order.jihuanshe_order_id == payload.jihuanshe_order_id)
        )
        if existing is not None:
            raise HTTPException(
                status_code=409,
                detail=f"La orden {payload.jihuanshe_order_id} ya existe (id {existing.id})",
            )
    return persist_order(db, payload)


@router.get("", response_model=list[OrderOut])
def list_orders(
    status: OrderStatus | None = None, db: Session = Depends(get_db)
) -> list[Order]:
    stmt = select(Order).options(_ORDER_LOAD).order_by(Order.created_at.desc())
    if status is not None:
        stmt = stmt.where(Order.status == status)
    return list(db.scalars(stmt))


@router.get("/{order_id}", response_model=OrderOut)
def get_order(order_id: str, db: Session = Depends(get_db)) -> Order:
    order = db.scalar(
        select(Order).options(_ORDER_LOAD).where(Order.id == order_id)
    )
    if order is None:
        raise HTTPException(status_code=404, detail="Orden no encontrada")
    return order


@router.get("/{order_id}/landed", response_model=LandedOut)
def order_landed(order_id: str, db: Session = Depends(get_db)) -> dict:
    order = db.scalar(
        select(Order).options(_ORDER_LOAD).where(Order.id == order_id)
    )
    if order is None:
        raise HTTPException(status_code=404, detail="Orden no encontrada")

    shipment = None
    if order.shipment_id:
        shipment = db.scalar(
            select(Shipment)
            .options(
                selectinload(Shipment.costs),
                selectinload(Shipment.orders).selectinload(Order.items).selectinload(OrderItem.card),
            )
            .where(Shipment.id == order.shipment_id)
        )
    return compute_order_landed(order, shipment)


@router.patch("/{order_id}/status", response_model=OrderOut)
def set_order_status(
    order_id: str, payload: OrderStatusIn, db: Session = Depends(get_db)
) -> Order:
    order = db.scalar(
        select(Order).options(_ORDER_LOAD).where(Order.id == order_id)
    )
    if order is None:
        raise HTTPException(status_code=404, detail="Orden no encontrada")
    order.status = payload.status
    db.commit()
    db.refresh(order)
    return order


@router.put("/{order_id}", response_model=OrderOut)
def update_order(order_id: str, payload: OrderIn, db: Session = Depends(get_db)) -> Order:
    order = db.scalar(
        select(Order).options(_ORDER_LOAD).where(Order.id == order_id)
    )
    if order is None:
        raise HTTPException(status_code=404, detail="Orden no encontrada")
    if payload.jihuanshe_order_id:
        duplicate = db.scalar(
            select(Order).where(
                Order.jihuanshe_order_id == payload.jihuanshe_order_id,
                Order.id != order_id,
            )
        )
        if duplicate is not None:
            raise HTTPException(status_code=409, detail="Ese número de pedido ya está guardado")
    try:
        return update_order_data(db, order, payload)
    except OrderEditError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
