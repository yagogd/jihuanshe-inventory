"""Shipment endpoints."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.db import get_db
from app.domain.models import Order, Shipment
from app.domain.schemas import ShipmentIn, ShipmentOut
from app.domain.shipments import create_shipment
from app.domain.shipments import update_shipment as update_shipment_data

router = APIRouter(prefix="/shipments", tags=["shipments"])


def _load(shipment_id: str, db: Session) -> Shipment:
    shipment = db.scalar(
        select(Shipment)
        .options(
            selectinload(Shipment.costs),
            selectinload(Shipment.orders).selectinload(Order.items),
        )
        .where(Shipment.id == shipment_id)
    )
    if shipment is None:
        raise HTTPException(status_code=404, detail="Envío no encontrado")
    return shipment


@router.post("", response_model=ShipmentOut, status_code=201)
def create(payload: ShipmentIn, db: Session = Depends(get_db)) -> Shipment:
    shipment = create_shipment(db, payload)
    return _load(shipment.id, db)


@router.get("", response_model=list[ShipmentOut])
def list_shipments(db: Session = Depends(get_db)) -> list[Shipment]:
    return list(
        db.scalars(
            select(Shipment)
            .options(
                selectinload(Shipment.costs),
                selectinload(Shipment.orders).selectinload(Order.items),
            )
            .order_by(Shipment.created_at.desc())
        )
    )


@router.get("/{shipment_id}", response_model=ShipmentOut)
def get_shipment(shipment_id: str, db: Session = Depends(get_db)) -> Shipment:
    return _load(shipment_id, db)


@router.put("/{shipment_id}", response_model=ShipmentOut)
def update_shipment(
    shipment_id: str, payload: ShipmentIn, db: Session = Depends(get_db)
) -> Shipment:
    shipment = _load(shipment_id, db)
    return update_shipment_data(db, shipment, payload)
