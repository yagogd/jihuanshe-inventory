"""Order endpoints."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.db import get_db
from app.domain.models import Order
from app.domain.orders import persist_order
from app.domain.orders import update_order as update_order_data
from app.domain.schemas import OrderIn, OrderOut

router = APIRouter(prefix="/orders", tags=["orders"])


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
def list_orders(db: Session = Depends(get_db)) -> list[Order]:
    return list(
        db.scalars(select(Order).options(selectinload(Order.items)).order_by(Order.created_at.desc()))
    )


@router.get("/{order_id}", response_model=OrderOut)
def get_order(order_id: str, db: Session = Depends(get_db)) -> Order:
    order = db.scalar(
        select(Order).options(selectinload(Order.items)).where(Order.id == order_id)
    )
    if order is None:
        raise HTTPException(status_code=404, detail="Orden no encontrada")
    return order


@router.put("/{order_id}", response_model=OrderOut)
def update_order(order_id: str, payload: OrderIn, db: Session = Depends(get_db)) -> Order:
    order = db.scalar(
        select(Order).options(selectinload(Order.items)).where(Order.id == order_id)
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
    return update_order_data(db, order, payload)
