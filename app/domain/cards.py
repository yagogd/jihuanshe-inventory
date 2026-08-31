"""Card catalog services: resolve identity and keep names translated.

A card is identified by ``(game, set_code, collector_number)``. The Chinese
name is stored as scraped; the English name is filled once (see
``app.domain.translate``) and never overwritten by later imports.
"""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.models import Card, OrderItem


def card_identity(
    game: str | None, set_code: str | None, collector_number: str | None
) -> tuple[str, str, str] | None:
    """Return the (game, set, number) key, or ``None`` when identity is incomplete.

    A card without set and number cannot be catalogued: the caller keeps the
    purchase unlinked instead of inventing an identity.
    """
    set_code = (set_code or "").strip()
    number = (collector_number or "").strip()
    if not set_code or not number:
        return None
    return ((game or "").strip(), set_code, number)


def resolve_card(
    db: Session,
    *,
    game: str | None,
    set_code: str | None,
    collector_number: str | None,
    raw_name: str | None = None,
    name_en: str | None = None,
    language: str | None = None,
    variant: str | None = None,
    foil: bool = False,
    promo: bool = False,
    image_path: str | None = None,
) -> Card | None:
    """Get-or-create the Card for an identity, filling missing attributes.

    Existing attributes are left untouched; a card already has a Chinese name
    and a translation, so re-importing the same card is a no-op on names.
    """
    identity = card_identity(game, set_code, collector_number)
    if identity is None:
        return None
    card_game, card_set, card_number = identity

    card = db.scalar(
        select(Card).where(
            Card.game == card_game,
            Card.set_code == card_set,
            Card.collector_number == card_number,
        )
    )
    if card is None:
        card = Card(game=card_game or None, set_code=card_set, collector_number=card_number)
        db.add(card)
        db.flush()

    if not card.name_zh and raw_name:
        card.name_zh = raw_name
    if name_en and not card.name_en:
        card.name_en = name_en
    if language and not card.language:
        card.language = language
    if variant and not card.variant:
        card.variant = variant
    card.foil = card.foil or foil
    card.promo = card.promo or promo
    if image_path and not card.image_path:
        card.image_path = image_path
    return card


def backfill_cards(db: Session) -> int:
    """Link existing order items to catalog Cards; create them when missing.

    Returns the number of items linked. Items without set/number are skipped.
    """
    items = list(
        db.scalars(
            select(OrderItem).where(OrderItem.card_id.is_(None)).order_by(OrderItem.position)
        )
    )
    linked = 0
    for item in items:
        card = resolve_card(
            db,
            game=item.game,
            set_code=item.set_code,
            collector_number=item.collector_number,
            raw_name=item.raw_name,
            language=item.language,
            variant=item.variant,
            foil=item.foil,
            promo=item.promo,
            image_path=item.image_path,
        )
        if card is not None:
            item.card_id = card.id
            linked += 1
    if linked:
        db.commit()
    return linked
