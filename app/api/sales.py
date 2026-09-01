"""Listing and sales endpoints."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.db import get_db
from app.domain.inventory import InventoryError
from app.domain.models import Bundle, BundleItem, BundleListing, InventoryLot, Listing, OrderItem, Sale
from app.domain.sales import (
    create_listing,
    create_bundle,
    bundle_to_dict,
    listing_to_dict,
    remove_listing,
    sale_to_dict,
    sell_listing,
    sell_bundle_listing,
    update_listing,
    update_sale,
)
from app.domain.schemas import BundleIn, BundleOut, BundleListingIn, ListingIn, ListingOut, ListingUpdateIn, SaleIn, SaleOut

listings_router = APIRouter(prefix="/listings", tags=["listings"])
sales_router = APIRouter(prefix="/sales", tags=["sales"])
bundles_router = APIRouter(tags=["bundles"])

_LOT_LOAD = (
    selectinload(Listing.lot).selectinload(InventoryLot.card),
    selectinload(Listing.lot).selectinload(InventoryLot.order_item).selectinload(OrderItem.order),
)
_SALE_LOAD = (
    selectinload(Sale.lot).selectinload(InventoryLot.card),
    selectinload(Sale.lot).selectinload(InventoryLot.order_item).selectinload(OrderItem.order),
    selectinload(Sale.bundle).selectinload(Bundle.items).selectinload(BundleItem.lot).selectinload(InventoryLot.card),
    selectinload(Sale.bundle).selectinload(Bundle.items).selectinload(BundleItem.lot).selectinload(InventoryLot.order_item).selectinload(OrderItem.order),
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
        listing = create_listing(
            db, lot, payload.quantity, payload.unit_price_eur_cents, payload.marketplace
        )
    except InventoryError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return listing_to_dict(_load_listing(listing.id, db))


@listings_router.put("/{listing_id}", response_model=ListingOut)
def update_listing_endpoint(
    listing_id: str, payload: ListingUpdateIn, db: Session = Depends(get_db)
) -> dict:
    listing = _load_listing(listing_id, db)
    try:
        update_listing(
            db, listing, payload.quantity, payload.unit_price_eur_cents,
            payload.marketplace,
        )
    except InventoryError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return listing_to_dict(listing)


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


@listings_router.delete("/{listing_id}", status_code=204)
def delete_listing_endpoint(listing_id: str, db: Session = Depends(get_db)) -> None:
    listing = _load_listing(listing_id, db)
    db.delete(listing)
    db.commit()


@sales_router.get("", response_model=list[SaleOut])
def list_sales(db: Session = Depends(get_db)) -> list[dict]:
    sales = list(
        db.scalars(select(Sale).options(*_SALE_LOAD).order_by(Sale.sold_at.desc()))
    )
    return [sale_to_dict(sale) for sale in sales]


@sales_router.put("/{sale_id}", response_model=SaleOut)
def update_sale_endpoint(sale_id: str, payload: SaleIn, db: Session = Depends(get_db)) -> dict:
    sale = db.scalar(select(Sale).options(*_SALE_LOAD).where(Sale.id == sale_id))
    if sale is None:
        raise HTTPException(status_code=404, detail="Venta no encontrada")
    try:
        update_sale(db, sale, payload.quantity, payload.unit_price_eur_cents, payload.fees_eur_cents)
    except InventoryError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return sale_to_dict(sale)


_BUNDLE_LOAD = (
    selectinload(Bundle.items).selectinload(BundleItem.lot).selectinload(InventoryLot.card),
    selectinload(Bundle.items).selectinload(BundleItem.lot).selectinload(InventoryLot.order_item).selectinload(OrderItem.order),
    selectinload(Bundle.listings),
)


def _load_bundle(bundle_id: str, db: Session) -> Bundle:
    bundle = db.scalar(select(Bundle).options(*_BUNDLE_LOAD).where(Bundle.id == bundle_id))
    if bundle is None:
        raise HTTPException(status_code=404, detail="Bundle no encontrado")
    return bundle


def _load_bundle_listing(listing_id: str, db: Session) -> BundleListing:
    listing = db.scalar(
        select(BundleListing).options(selectinload(BundleListing.bundle)).where(BundleListing.id == listing_id)
    )
    if listing is None:
        raise HTTPException(status_code=404, detail="Anuncio de bundle no encontrado")
    _load_bundle(listing.bundle_id, db)
    return listing


@bundles_router.get("/bundles", response_model=list[BundleOut])
def list_bundles(db: Session = Depends(get_db)) -> list[dict]:
    bundles = list(db.scalars(select(Bundle).options(*_BUNDLE_LOAD).order_by(Bundle.created_at.desc())))
    return [bundle_to_dict(bundle) for bundle in bundles]


@bundles_router.post("/bundles", response_model=BundleOut, status_code=201)
def create_bundle_endpoint(payload: BundleIn, db: Session = Depends(get_db)) -> dict:
    try:
        bundle = create_bundle(db, payload.name, payload.items, payload.listings)
    except InventoryError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return bundle_to_dict(_load_bundle(bundle.id, db))


@bundles_router.put("/bundle-listings/{listing_id}", response_model=BundleOut)
def update_bundle_listing_endpoint(listing_id: str, payload: BundleListingIn, db: Session = Depends(get_db)) -> dict:
    listing = _load_bundle_listing(listing_id, db)
    bundle = _load_bundle(listing.bundle_id, db)
    if listing.status not in ("ACTIVE", "NEEDS_REMOVAL"):
        raise HTTPException(status_code=422, detail="Este anuncio ya no se puede editar")
    if any(item.lot.available < item.quantity for item in bundle.items):
        raise HTTPException(status_code=422, detail="No hay stock suficiente para reactivar el bundle")
    listing.marketplace = payload.marketplace.strip().upper()
    listing.unit_price_eur_cents = payload.unit_price_eur_cents
    listing.status = "ACTIVE"
    db.commit()
    return bundle_to_dict(bundle)


@bundles_router.post("/bundle-listings/{listing_id}/sell", response_model=BundleOut)
def sell_bundle_listing_endpoint(listing_id: str, payload: SaleIn, db: Session = Depends(get_db)) -> dict:
    listing = _load_bundle_listing(listing_id, db)
    try:
        bundle = sell_bundle_listing(db, listing, payload.unit_price_eur_cents, payload.fees_eur_cents)
    except InventoryError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return bundle_to_dict(_load_bundle(bundle.id, db))


@bundles_router.delete("/bundle-listings/{listing_id}", status_code=204)
def delete_bundle_listing_endpoint(listing_id: str, db: Session = Depends(get_db)) -> None:
    listing = _load_bundle_listing(listing_id, db)
    db.delete(listing)
    db.commit()
