from fastapi.testclient import TestClient

from app.main import app


def test_settings_roundtrip():
    with TestClient(app) as client:
        body = client.get("/api/settings").json()
        assert body["alipay_fee_threshold_fen"] == 20000
        assert body["alipay_fee_rate"] == 0.03
        assert body["fx_cny_eur"] == 0.13
        assert body["inventory_page_size"] == 20

        updated = client.put(
            "/api/settings",
            json={"fx_cny_eur": 0.14, "alipay_fee_rate": 0.02, "inventory_page_size": 35},
        ).json()
        assert updated["fx_cny_eur"] == 0.14
        assert updated["alipay_fee_rate"] == 0.02
        assert updated["inventory_page_size"] == 35

        again = client.get("/api/settings").json()
        assert again["fx_cny_eur"] == 0.14
        assert again["alipay_fee_rate"] == 0.02
        assert again["inventory_page_size"] == 35


def _order_payload():
    return {
        "seller": "v",
        "domestic_shipping_fen": 0,
        "fx_cny_eur": 0.13,
        "items": [
            {"raw_name": "carta", "quantity": 1, "unit_price_fen": 15000, "origin": "SCRAPED"},
        ],
    }


def test_saved_fees_not_overwritten_on_settings_change():
    with TestClient(app) as client:
        client.put("/api/settings", json={"alipay_fee_threshold_fen": 10000, "alipay_fee_rate": 0.03})
        created = client.post("/api/orders", json=_order_payload())
        assert created.status_code == 201, created.text
        body = created.json()
        # 150.00 > 100.00 -> 3% of 150 = 4.50 -> 450 fen
        assert body["alipay_fee_fen"] == 450

        client.put("/api/settings", json={"alipay_fee_threshold_fen": 20000})
        detail = client.get(f"/api/orders/{body['id']}").json()
        assert detail["alipay_fee_fen"] == 450


def test_custom_marketplace_can_be_created_and_listed():
    with TestClient(app) as client:
        created = client.post("/api/settings/marketplaces", json={
            "name": "TCG Player",
            "icon_path": "manual/tcg.png",
        })
        assert created.status_code == 201, created.text
        assert created.json()["code"] == "TCG_PLAYER"
        assert created.json()["icon_path"] == "manual/tcg.png"

        marketplaces = client.get("/api/settings/marketplaces").json()
        assert any(row["code"] == "CARDMARKET" and row["builtin"] for row in marketplaces)
        assert any(row["code"] == "TCG_PLAYER" and not row["builtin"] for row in marketplaces)

        edited = client.put("/api/settings/marketplaces/TCG_PLAYER", json={
            "name": "TCGplayer Europe",
            "icon_path": "manual/tcg-new.png",
        })
        assert edited.status_code == 200, edited.text
        assert edited.json()["code"] == "TCG_PLAYER"
        assert edited.json()["name"] == "TCGplayer Europe"
        assert edited.json()["icon_path"] == "manual/tcg-new.png"


def test_builtin_marketplace_can_be_edited_and_removed():
    with TestClient(app) as client:
        edited = client.put("/api/settings/marketplaces/EBAY", json={
            "name": "Mi eBay",
            "icon_path": "manual/my-ebay.png",
        })
        assert edited.status_code == 200, edited.text
        assert edited.json()["code"] == "EBAY"
        assert edited.json()["name"] == "Mi eBay"
        assert edited.json()["builtin"] is True

        removed = client.delete("/api/settings/marketplaces/EBAY")
        assert removed.status_code == 204, removed.text
        assert all(row["code"] != "EBAY" for row in client.get("/api/settings/marketplaces").json())
