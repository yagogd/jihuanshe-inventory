"""Chinese → English name translation, cached on the Card itself.

The translation is a best-effort, one-shot network call per new card. Once the
English name is stored it is never re-translated; the user can edit it or ask
for a batch translation of everything still missing.
"""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.domain.models import Card
from app.infra.translate_http import translate_zh_to_en


def ensure_english_name(db: Session, card: Card) -> bool:
    """Translate ``card.name_zh`` into ``card.name_en`` when missing.

    Gated by ``auto_translate`` for the import path. Returns ``True`` when a
    translation was stored.
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


def translate_card(db: Session, card: Card) -> bool:
    """Force-translate a single card regardless of ``auto_translate``."""
    if card.name_en or not card.name_zh:
        return False
    translated = translate_zh_to_en(card.name_zh)
    if translated:
        card.name_en = translated
        db.commit()
        db.refresh(card)
        return True
    return False


def translate_all(db: Session) -> int:
    """Force-translate every card still missing an English name."""
    cards = list(
        db.scalars(
            select(Card)
            .where(Card.name_en.is_(None))
            .where(Card.name_zh.is_not(None))
        )
    )
    translated = 0
    for card in cards:
        result = translate_zh_to_en(card.name_zh)
        if result:
            card.name_en = result
            translated += 1
    if translated:
        db.commit()
    return translated
