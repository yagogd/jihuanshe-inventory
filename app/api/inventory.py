"""Inventory endpoints: lots, movements, splits and manual additions."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.db import get_db
from app.domain.inventory import (
    InventoryError,
    add_manual_lot,
    add_movement,
    lot_to_dict,
    split_lot,
)
from app.domain.models import InventoryLot, OrderItem
from app.domain.sales import sale_to_dict, sell_lot
from app.domain.schemas import (
    InventoryLotDetailOut,
    InventoryLotIn,
    InventoryLotOut,
    MovementIn,
    SaleIn,
    SaleOut,
    SplitIn,
)

router = APIRouter(prefix="/inventory", tags=["inventory"])


def _load_lot(lot_id: str, db: Session) -> InventoryLot:
    lot = db.scalar(
        select(InventoryLot)
        .options(
            selectinload(InventoryLot.order_item).selectinload(OrderItem.order),
            selectinload(InventoryLot.card),
            selectinload(InventoryLot.movements),
        )
        .where(InventoryLot.id == lot_id)
    )
    if lot is None:
        raise HTTPException(status_code=404, detail="Lote no encontrado")
    return lot


@router.post("", response_model=InventoryLotOut, status_code=201)
def add_lot(payload: InventoryLotIn, db: Session = Depends(get_db)) -> dict:
    try:
        lot = add_manual_lot(db, payload)
    except InventoryError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return lot_to_dict(_load_lot(lot.id, db))


@router.get("", response_model=list[InventoryLotOut])
def list_inventory(
    q: str | None = None,
    game: str | None = None,
    set_code: str | None = None,
    condition: str | None = None,
    available_only: bool = False,
    db: Session = Depends(get_db),
) -> list[dict]:
    lots = list(
        db.scalars(
            select(InventoryLot)
            .options(
                selectinload(InventoryLot.order_item).selectinload(OrderItem.order),
                selectinload(InventoryLot.card),
            )
            .order_by(InventoryLot.created_at.desc())
        )
    )

    result = []
    for lot in lots:
        data = lot_to_dict(lot)
        if q and q.lower() not in data["name"].lower() and q.lower() not in (data["raw_name"] or "").lower():
            continue
        if game and data["game"] != game:
            continue
        if set_code and data["set_code"] != set_code:
            continue
        if condition and data["condition"] != condition:
            continue
        if available_only and data["available"] <= 0:
            continue
        result.append(data)
    return result


@router.get("/{lot_id}", response_model=InventoryLotDetailOut)
def get_lot(lot_id: str, db: Session = Depends(get_db)) -> dict:
    lot = _load_lot(lot_id, db)
    data = lot_to_dict(lot)
    data["movements"] = list(lot.movements)
    return data


@router.post("/{lot_id}/split", response_model=InventoryLotOut, status_code=201)
def split(lot_id: str, payload: SplitIn, db: Session = Depends(get_db)) -> dict:
    lot = _load_lot(lot_id, db)
    try:
        new_lot = split_lot(db, lot, payload.quantity)
    except InventoryError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return lot_to_dict(new_lot)


@router.post("/{lot_id}/movements", response_model=InventoryLotOut)
def move(lot_id: str, payload: MovementIn, db: Session = Depends(get_db)) -> dict:
    lot = _load_lot(lot_id, db)
    try:
        add_movement(db, lot, payload.kind, payload.quantity)
    except InventoryError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return lot_to_dict(lot)


@router.post("/{lot_id}/sell", response_model=SaleOut)
def sell(lot_id: str, payload: SaleIn, db: Session = Depends(get_db)) -> dict:
    lot = _load_lot(lot_id, db)
    try:
        sale = sell_lot(db, lot, payload.quantity, payload.unit_price_eur_cents, payload.fees_eur_cents)
    except InventoryError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return sale_to_dict(sale)
