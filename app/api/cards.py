"""Card catalog endpoints."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db import get_db
from app.domain.cards import card_detail, list_cards, rename_card
from app.domain.models import Card
from app.domain.schemas import CardDetailOut, CardNameIn, CardOut
from app.domain.translate import translate_all, translate_card

router = APIRouter(prefix="/cards", tags=["cards"])


def _load(card_id: str, db: Session) -> Card:
    card = db.get(Card, card_id)
    if card is None:
        raise HTTPException(status_code=404, detail="Carta no encontrada")
    return card


@router.post("/translate")
def translate_cards_endpoint(db: Session = Depends(get_db)) -> dict:
    return {"translated": translate_all(db)}


@router.get("", response_model=list[CardOut])
def list_cards_endpoint(
    q: str | None = None,
    sort: str = "name_en",
    order: str = "asc",
    db: Session = Depends(get_db),
) -> list[dict]:
    return list_cards(db, q=q, sort=sort, order=order)


@router.post("/{card_id}/translate", response_model=CardOut)
def translate_card_endpoint(card_id: str, db: Session = Depends(get_db)) -> dict:
    card = _load(card_id, db)
    translate_card(db, card)
    return card_detail(db, card)


@router.get("/{card_id}", response_model=CardDetailOut)
def get_card(card_id: str, db: Session = Depends(get_db)) -> dict:
    return card_detail(db, _load(card_id, db))


@router.put("/{card_id}", response_model=CardOut)
def update_card(card_id: str, payload: CardNameIn, db: Session = Depends(get_db)) -> dict:
    card = rename_card(db, _load(card_id, db), payload.name_en)
    return card_detail(db, card)
