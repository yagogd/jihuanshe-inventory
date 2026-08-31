"""HTTP translation provider (no API key, stdlib only).

Uses the MyMemory free endpoint. Failures (no network, quota, bad response)
return ``None`` so callers can degrade gracefully instead of blocking an import.
"""
from __future__ import annotations

import json
from urllib.parse import urlencode
from urllib.request import urlopen

_ENDPOINT = "https://api.mymemory.translated.net/get"


def translate_zh_to_en(text: str, timeout: float = 3.0) -> str | None:
    if not text or not text.strip():
        return None
    try:
        query = urlencode({"q": text.strip(), "langpair": "zh-CN|en"})
        with urlopen(f"{_ENDPOINT}?{query}", timeout=timeout) as response:
            payload = json.loads(response.read().decode("utf-8"))
        translated = payload.get("responseData", {}).get("translatedText")
        if translated and translated.strip() and translated.strip() != text.strip():
            return translated.strip()
    except Exception:
        return None
    return None
