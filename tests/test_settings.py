from fastapi.testclient import TestClient

from app.main import app


def test_settings_roundtrip():
    with TestClient(app) as client:
        body = client.get("/api/settings").json()
        assert body["alipay_fee_threshold_fen"] == 20000
        assert body["alipay_fee_rate"] == 0.03
        assert body["fx_cny_eur"] == 0.13

        updated = client.put(
            "/api/settings",
            json={"fx_cny_eur": 0.14, "alipay_fee_rate": 0.02},
        ).json()
        assert updated["fx_cny_eur"] == 0.14
        assert updated["alipay_fee_rate"] == 0.02

        again = client.get("/api/settings").json()
        assert again["fx_cny_eur"] == 0.14
        assert again["alipay_fee_rate"] == 0.02


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
