"""Business settings endpoints."""
from __future__ import annotations

import re
import unicodedata

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.domain.models import AppSettings, Marketplace
from app.domain.schemas import MarketplaceIn, MarketplaceOut, SettingsIn, SettingsOut
from app.domain.settings import get_app_settings, update_app_settings

router = APIRouter(prefix="/settings", tags=["settings"])

_BUILTIN_MARKETPLACES = (
    {"code": "CARDMARKET", "name": "Cardmarket", "icon_path": None, "builtin": True},
    {"code": "EBAY", "name": "eBay", "icon_path": None, "builtin": True},
    {"code": "WALLAPOP", "name": "Wallapop", "icon_path": None, "builtin": True},
)


@router.get("", response_model=SettingsOut)
def read_settings(db: Session = Depends(get_db)) -> AppSettings:
    return get_app_settings(db)


@router.put("", response_model=SettingsOut)
def save_settings(payload: SettingsIn, db: Session = Depends(get_db)) -> AppSettings:
    return update_app_settings(db, payload)


@router.get("/marketplaces", response_model=list[MarketplaceOut])
def list_marketplaces(db: Session = Depends(get_db)) -> list[dict]:
    rows = list(db.scalars(select(Marketplace).order_by(Marketplace.name)))
    overrides = {row.code: row for row in rows}
    result = []
    builtin_codes = {item["code"] for item in _BUILTIN_MARKETPLACES}
    for default in _BUILTIN_MARKETPLACES:
        override = overrides.get(default["code"])
        if override is not None and not override.enabled:
            continue
        result.append({
            **default,
            "name": override.name if override else default["name"],
            "icon_path": override.icon_path if override else default["icon_path"],
        })
    result.extend(
        {"code": row.code, "name": row.name, "icon_path": row.icon_path, "builtin": False}
        for row in rows if row.code not in builtin_codes and row.enabled
    )
    return result


@router.post("/marketplaces", response_model=MarketplaceOut, status_code=201)
def create_marketplace(payload: MarketplaceIn, db: Session = Depends(get_db)) -> dict:
    name = payload.name.strip()
    if not name:
        raise HTTPException(status_code=422, detail="Indica el nombre del marketplace")
    normalized = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode()
    base = re.sub(r"[^A-Z0-9]+", "_", normalized.upper()).strip("_")[:20] or "MARKETPLACE"
    reserved = {row["code"] for row in _BUILTIN_MARKETPLACES}
    code = base
    suffix = 2
    while code in reserved or db.get(Marketplace, code) is not None:
        marker = f"_{suffix}"
        code = f"{base[:20 - len(marker)]}{marker}"
        suffix += 1
    row = Marketplace(code=code, name=name, icon_path=payload.icon_path)
    db.add(row)
    db.commit()
    return {"code": row.code, "name": row.name, "icon_path": row.icon_path, "builtin": False}


@router.put("/marketplaces/{code}", response_model=MarketplaceOut)
def update_marketplace(
    code: str, payload: MarketplaceIn, db: Session = Depends(get_db)
) -> dict:
    builtin_codes = {item["code"] for item in _BUILTIN_MARKETPLACES}
    row = db.get(Marketplace, code)
    if row is None and code not in builtin_codes:
        raise HTTPException(status_code=404, detail="Marketplace no encontrado")
    name = payload.name.strip()
    if not name:
        raise HTTPException(status_code=422, detail="Indica el nombre del marketplace")
    duplicate = db.scalar(
        select(Marketplace).where(Marketplace.name == name, Marketplace.code != code)
    )
    if duplicate is not None:
        raise HTTPException(status_code=422, detail="Ya existe un marketplace con ese nombre")
    if row is None:
        row = Marketplace(code=code, name=name, icon_path=payload.icon_path, enabled=True)
        db.add(row)
    else:
        row.name = name
        row.icon_path = payload.icon_path
        row.enabled = True
    db.commit()
    return {"code": row.code, "name": row.name, "icon_path": row.icon_path, "builtin": code in builtin_codes}


@router.delete("/marketplaces/{code}", status_code=204)
def delete_marketplace(code: str, db: Session = Depends(get_db)) -> None:
    builtin = next((item for item in _BUILTIN_MARKETPLACES if item["code"] == code), None)
    row = db.get(Marketplace, code)
    if row is None and builtin is None:
        raise HTTPException(status_code=404, detail="Marketplace no encontrado")
    if builtin is not None:
        if row is None:
            row = Marketplace(code=code, name=builtin["name"], icon_path=None, enabled=False)
            db.add(row)
        else:
            row.enabled = False
    else:
        db.delete(row)
    db.commit()
