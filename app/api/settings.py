"""Business settings endpoints."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db import get_db
from app.domain.models import AppSettings
from app.domain.schemas import SettingsIn, SettingsOut
from app.domain.settings import get_app_settings, update_app_settings

router = APIRouter(prefix="/settings", tags=["settings"])


@router.get("", response_model=SettingsOut)
def read_settings(db: Session = Depends(get_db)) -> AppSettings:
    return get_app_settings(db)


@router.put("", response_model=SettingsOut)
def save_settings(payload: SettingsIn, db: Session = Depends(get_db)) -> AppSettings:
    return update_app_settings(db, payload)
