from fastapi.testclient import TestClient

from app.main import app


def _create_card(client: TestClient, name: str, set_code: str, number: str) -> None:
    response = client.post(
        "/api/orders",
        json={
            "seller": "s",
            "items": [
                {
                    "raw_name": name,
                    "game": "符文战场",
                    "set_code": set_code,
                    "collector_number": number,
                    "quantity": 2,
                    "unit_price_fen": 1000,
                }
            ],
        },
    )
    assert response.status_code == 201, response.text


def test_cards_list_search_and_sort():
    with TestClient(app) as client:
        _create_card(client, "甲卡", "AAA", "001/100")
        _create_card(client, "乙卡", "BBB", "002/100")

        cards = client.get("/api/cards").json()
        assert len(cards) >= 2

        found = client.get("/api/cards", params={"q": "BBB"}).json()
        assert len(found) == 1
        assert found[0]["set_code"] == "BBB"

        by_set = client.get("/api/cards", params={"sort": "set_code", "order": "asc"}).json()
        sets = [c["set_code"] for c in by_set if c["set_code"]]
        assert sets == sorted(sets)


def test_card_detail_and_rename():
    with TestClient(app) as client:
        _create_card(client, "丙卡", "CCC", "003/100")

        card = next(c for c in client.get("/api/cards").json() if c["set_code"] == "CCC")
        detail = client.get(f"/api/cards/{card['id']}").json()
        assert detail["total_qty"] == 2
        assert len(detail["purchases"]) == 1

        renamed = client.put(f"/api/cards/{card['id']}", json={"name_en": "Card Three"}).json()
        assert renamed["name_en"] == "Card Three"

        card_after = client.get(f"/api/cards/{card['id']}").json()
        assert card_after["name_en"] == "Card Three"
