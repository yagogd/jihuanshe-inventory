"""Condition normalization to Cardmarket-style grade codes.

Jihuanshe reports a generic ``流通品相`` ("circulation condition") label; cards
from there are treated as Near Mint by default. Any missing condition also
defaults to ``NM``.
"""
from __future__ import annotations

_CHINESE_CONDITIONS = {
    "流通品相": "NM",
    "近全新": "NM",
    "全新": "M",
}

DEFAULT_CONDITION = "NM"


def normalize_condition(value: str | None) -> str:
    if not value:
        return DEFAULT_CONDITION
    stripped = value.strip()
    return _CHINESE_CONDITIONS.get(stripped, stripped.upper())
