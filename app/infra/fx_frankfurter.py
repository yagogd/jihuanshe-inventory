"""Frankfurter/ECB exchange-rate provider (stdlib only, no API key).

Rates are expressed as units of EUR per one unit of ``quote`` currency, i.e.
the multiplier to convert ``quote`` amounts into EUR. Failures (offline, bad
date, quota) return ``None`` so callers fall back to a fixed rate.
"""
from __future__ import annotations

import json
from urllib.request import urlopen

_ENDPOINT = "https://api.frankfurter.app"


def fetch_eur_per(date: str, quote: str, timeout: float = 4.0) -> float | None:
    if quote == "EUR":
        return 1.0
    if not date or not quote:
        return None
    try:
        url = f"{_ENDPOINT}/{date}?from={quote}&to=EUR"
        with urlopen(url, timeout=timeout) as response:
            payload = json.loads(response.read().decode("utf-8"))
        rate = payload.get("rates", {}).get("EUR")
        if isinstance(rate, (int, float)) and rate > 0:
            return float(rate)
    except Exception:
        return None
    return None
