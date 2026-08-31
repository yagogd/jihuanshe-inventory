"""Chinese → English name translation, cached on the Card itself.

The translation is a best-effort, one-shot network call per new card. Once the
English name is stored it is never re-translated; the user can edit it in the
catalog. No network means the card simply keeps an empty English name.
"""
from __future__ import annotations

from sqlalchemy.orm import Session

from app.config import get_settings
from app.domain.models import Card
from app.infra.translate_http import translate_zh_to_en


def ensure_english_name(db: Session, card: Card) -> bool:
    """Translate ``card.name_zh`` into ``card.name_en`` when missing.

    Returns ``True`` when a translation was stored. Skips cleanly when the card
    already has an English name, lacks a Chinese name, or auto-translate is off.
    """
    if not card.name_en and card.name_zh and get_settings().auto_translate:
        translated = translate_zh_to_en(card.name_zh)
        if translated:
            card.name_en = translated
            return True
    return False


def translate_cards(db: Session, cards: list[Card]) -> int:
    """Translate every card in the list that still lacks an English name."""
    translated = 0
    for card in cards:
        if ensure_english_name(db, card):
            translated += 1
    return translated
