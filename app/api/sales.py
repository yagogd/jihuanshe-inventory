"""Listing and sales endpoints."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.db import get_db
from app.domain.inventory import InventoryError
from app.domain.models import InventoryLot, Listing, OrderItem, Sale
from app.domain.sales import (
    create_listing,
    listing_to_dict,
    remove_listing,
    sale_to_dict,
    sell_listing,
)
from app.domain.schemas import ListingIn, ListingOut, SaleIn, SaleOut

listings_router = APIRouter(prefix="/listings", tags=["listings"])
sales_router = APIRouter(prefix="/sales", tags=["sales"])

_LOT_LOAD = (
    selectinload(Listing.lot).selectinload(InventoryLot.card),
    selectinload(Listing.lot).selectinload(InventoryLot.order_item).selectinload(OrderItem.order),
)
_SALE_LOAD = (
    selectinload(Sale.lot).selectinload(InventoryLot.card),
    selectinload(Sale.lot).selectinload(InventoryLot.order_item).selectinload(OrderItem.order),
)


def _load_listing(listing_id: str, db: Session) -> Listing:
    listing = db.scalar(
        select(Listing).options(*_LOT_LOAD).where(Listing.id == listing_id)
    )
    if listing is None:
        raise HTTPException(status_code=404, detail="Listado no encontrado")
    return listing


@listings_router.get("", response_model=list[ListingOut])
def list_listings(db: Session = Depends(get_db)) -> list[dict]:
    listings = list(
        db.scalars(select(Listing).options(*_LOT_LOAD).order_by(Listing.created_at.desc()))
    )
    return [listing_to_dict(listing) for listing in listings]


@listings_router.post("", response_model=ListingOut, status_code=201)
def create_listing_endpoint(payload: ListingIn, db: Session = Depends(get_db)) -> dict:
    lot = db.scalar(
        select(InventoryLot)
        .options(
            selectinload(InventoryLot.card),
            selectinload(InventoryLot.order_item).selectinload(OrderItem.order),
        )
        .where(InventoryLot.id == payload.lot_id)
    )
    if lot is None:
        raise HTTPException(status_code=404, detail="Lote no encontrado")
    try:
        listing = create_listing(db, lot, payload.quantity, payload.unit_price_eur_cents)
    except InventoryError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return listing_to_dict(_load_listing(listing.id, db))


@listings_router.post("/{listing_id}/sell", response_model=SaleOut)
def sell_listing_endpoint(
    listing_id: str, payload: SaleIn, db: Session = Depends(get_db)
) -> dict:
    listing = _load_listing(listing_id, db)
    try:
        sale = sell_listing(
            db, listing, payload.quantity, payload.unit_price_eur_cents, payload.fees_eur_cents
        )
    except InventoryError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return sale_to_dict(sale)


@listings_router.post("/{listing_id}/remove", response_model=ListingOut)
def remove_listing_endpoint(listing_id: str, db: Session = Depends(get_db)) -> dict:
    listing = _load_listing(listing_id, db)
    remove_listing(db, listing)
    return listing_to_dict(listing)


@sales_router.get("", response_model=list[SaleOut])
def list_sales(db: Session = Depends(get_db)) -> list[dict]:
    sales = list(
        db.scalars(select(Sale).options(*_SALE_LOAD).order_by(Sale.sold_at.desc()))
    )
    return [sale_to_dict(sale) for sale in sales]
