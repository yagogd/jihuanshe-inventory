"""FX policy: how a CNY→EUR rate is chosen and frozen on an order.

The rate is resolved once per order and stored with ``fx_source``:

- ``historical`` — fetched from the ECB for the purchase date (estimated).
- ``fixed``      — the fixed rate configured in settings (estimated).
- ``card``       — derived from the exact EUR the card was charged (confirmed).

The distinction between estimated and confirmed is what the UI surfaces; the
actual math only depends on the stored rate and, when present, the card charge.
"""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.models import AppSettings, FxRate
from app.domain.settings import get_app_settings
from app.infra.fx_frankfurter import fetch_eur_per


def _cached_or_fetch(db: Session, date: str, quote: str) -> float | None:
    row = db.scalar(
        select(FxRate).where(FxRate.date == date, FxRate.quote == quote)
    )
    if row is not None:
        return row.rate
    rate = fetch_eur_per(date, quote)
    if rate is None:
        return None
    db.add(FxRate(date=date, quote=quote, rate=rate))
    db.commit()
    return rate


def resolve_cny_eur(db: Session, date: str | None) -> tuple[float, str]:
    """Return (rate, source) for a CNY→EUR conversion on the given date."""
    settings = get_app_settings(db)
    if settings.fx_mode == "fixed":
        return settings.fx_cny_eur, "fixed"
    if date:
        rate = _cached_or_fetch(db, date, "CNY")
        if rate is not None:
            return rate, "historical"
    return settings.fx_cny_eur, "fixed"


def convert_to_eur(amount: int, currency: str, db: Session, date: str | None = None) -> int:
    """Convert an integer amount (minor units) into EUR cents.

    ``currency`` is one of ``EUR``, ``CNY``, ``USD``. EUR is identity; the
    others use the ECB rate for ``date`` (today's latest when date is None).
    Offline falls back to the settings fixed rate (CNY) or a rough constant (USD).
    """
    if currency == "EUR":
        return amount
    quote = "CNY" if currency == "CNY" else "USD"
    if date is None:
        date = datetime.now(timezone.utc).date().isoformat()
    rate = _cached_or_fetch(db, date, quote)
    if rate is not None:
        return round(amount * rate)
    settings: AppSettings = get_app_settings(db)
    if currency == "CNY":
        return round(amount * settings.fx_cny_eur)
    return round(amount * 0.92)
