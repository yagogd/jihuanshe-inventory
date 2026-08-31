from fastapi.testclient import TestClient
from sqlalchemy import select

from app.db import SessionLocal, init_db
from app.domain.cards import card_identity, resolve_card
from app.domain.models import Card, OrderItem
from app.main import app


def test_card_identity_requires_set_and_number():
    assert card_identity("符文战场", "OGN", "078/298") == ("符文战场", "OGN", "078/298")
    assert card_identity(None, "OGN", "078/298") == ("", "OGN", "078/298")
    assert card_identity("符文战场", None, "078/298") is None
    assert card_identity("符文战场", "OGN", None) is None


def test_resolve_creates_then_reuses():
    init_db()
    with SessionLocal() as db:
        first = resolve_card(
            db,
            game="符文战场",
            set_code="OGN",
            collector_number="078/298",
            raw_name="李青, 苦修者",
        )
        second = resolve_card(
            db,
            game="符文战场",
            set_code="OGN",
            collector_number="078/298",
            raw_name="李青, 苦修者",
        )
        db.commit()
        assert first is not None and first.id == second.id
        assert second.name_zh == "李青, 苦修者"
        matches = list(
            db.scalars(
                select(Card).where(
                    Card.game == "符文战场",
                    Card.set_code == "OGN",
                    Card.collector_number == "078/298",
                )
            )
        )
        assert len(matches) == 1


def test_import_links_items_to_cards():
    with TestClient(app) as client:
        created = client.post(
            "/api/orders",
            json={
                "seller": "s",
                "items": [
                    {
                        "raw_name": "卡牌链接测试",
                        "game": "符文战场",
                        "set_code": "ZZZ",
                        "collector_number": "999/298",
                        "quantity": 2,
                        "unit_price_fen": 1000,
                    }
                ],
            },
        )
        assert created.status_code == 201, created.text

    with SessionLocal() as db:
        items = list(
            db.scalars(select(OrderItem).where(OrderItem.raw_name == "卡牌链接测试"))
        )
        assert len(items) == 1
        assert items[0].card_id is not None
        card = db.get(Card, items[0].card_id)
        assert card.name_zh == "卡牌链接测试"
        assert card.set_code == "ZZZ"
