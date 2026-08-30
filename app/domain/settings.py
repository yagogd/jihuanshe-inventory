"""Runtime business settings: single-row access + update.

Environment variables seed the row on first access; afterwards the row in
SQLite is authoritative. Kept free of FastAPI so it can be used from both the
API layer and the domain services.
"""
from __future__ import annotations

from sqlalchemy.orm import Session

from app.config import get_settings
from app.domain.models import AppSettings
from app.domain.schemas import SettingsIn

SETTINGS_ROW_ID = 1


def get_app_settings(db: Session) -> AppSettings:
    row = db.get(AppSettings, SETTINGS_ROW_ID)
    if row is None:
        config = get_settings()
        row = AppSettings(
            id=SETTINGS_ROW_ID,
            alipay_fee_threshold_fen=config.alipay_fee_threshold_fen,
            alipay_fee_rate=config.alipay_fee_rate,
            fx_cny_eur=config.fx_cny_eur,
        )
        db.add(row)
        db.commit()
        db.refresh(row)
    return row


def update_app_settings(db: Session, payload: SettingsIn) -> AppSettings:
    row = get_app_settings(db)
    if payload.alipay_fee_threshold_fen is not None:
        row.alipay_fee_threshold_fen = payload.alipay_fee_threshold_fen
    if payload.alipay_fee_rate is not None:
        row.alipay_fee_rate = payload.alipay_fee_rate
    if payload.fx_cny_eur is not None:
        row.fx_cny_eur = payload.fx_cny_eur
    db.commit()
    db.refresh(row)
    return row
