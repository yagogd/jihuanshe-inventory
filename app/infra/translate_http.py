"""HTTP translation providers (no API key, stdlib only).

Tries Google's free endpoint first (what the user already trusts), then
MyMemory as a fallback. Failures return ``None`` so callers degrade gracefully.
"""
from __future__ import annotations

import json
from urllib.parse import urlencode
from urllib.request import Request, urlopen

_GOOGLE = "https://translate.googleapis.com/translate_a/single"
_MYMEMORY = "https://api.mymemory.translated.net/get"


def _google(text: str, timeout: float) -> str | None:
    query = urlencode({"client": "gtx", "sl": "zh-CN", "tl": "en", "dt": "t", "q": text})
    request = Request(f"{_GOOGLE}?{query}", headers={"User-Agent": "Mozilla/5.0"})
    with urlopen(request, timeout=timeout) as response:
        payload = json.loads(response.read().decode("utf-8"))
    parts = [segment[0] for segment in payload[0] if segment and segment[0]]
    return "".join(parts).strip()


def _mymemory(text: str, timeout: float) -> str | None:
    query = urlencode({"q": text, "langpair": "zh-CN|en"})
    with urlopen(f"{_MYMEMORY}?{query}", timeout=timeout) as response:
        payload = json.loads(response.read().decode("utf-8"))
    return payload.get("responseData", {}).get("translatedText")


def translate_zh_to_en(text: str, timeout: float = 3.0) -> str | None:
    if not text or not text.strip():
        return None
    source = text.strip()
    for provider in (_google, _mymemory):
        for attempt in range(2):
            try:
                translated = provider(source, timeout)
            except Exception:
                continue
            if translated and translated.strip() and translated.strip() != source:
                return translated.strip()
    return None
