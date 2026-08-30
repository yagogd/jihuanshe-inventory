from fastapi.testclient import TestClient

from app.main import app


def _order(client: TestClient, name: str, quantity: int) -> str:
    response = client.post(
        "/api/orders",
        json={
            "seller": "s",
            "items": [{"raw_name": name, "quantity": quantity, "unit_price_fen": 1000}],
        },
    )
    assert response.status_code == 201, response.text
    return response.json()["id"]


def _receive(client: TestClient, order_id: str) -> str:
    shipment = client.post("/api/shipments", json={"order_ids": [order_id], "costs": []}).json()
    response = client.post(f"/api/shipments/{shipment['id']}/receive")
    assert response.status_code == 200, response.text
    return shipment["id"]


def _lot(client: TestClient, name: str) -> dict:
    return client.get("/api/inventory", params={"q": name}).json()[0]


def test_sell_from_inventory_records_sale_with_profit():
    with TestClient(app) as client:
        order_id = _order(client, "VentaAlpha", 2)
        _receive(client, order_id)
        lot = _lot(client, "VentaAlpha")

        sale = client.post(
            f"/api/inventory/{lot['id']}/sell",
            json={"quantity": 1, "unit_price_eur_cents": 200, "fees_eur_cents": 10},
        )
        assert sale.status_code == 200, sale.text
        body = sale.json()
        assert body["landed_unit_eur_cents"] == 130
        assert body["revenue_eur_cents"] == 200
        assert body["cost_eur_cents"] == 140  # 130 landed + 10 fees
        assert body["profit_eur_cents"] == 60

        assert _lot(client, "VentaAlpha")["available"] == 1

        sales = client.get("/api/sales").json()
        assert any(s["id"] == body["id"] for s in sales)


def test_listing_sell_marks_sold():
    with TestClient(app) as client:
        order_id = _order(client, "VentaBeta", 2)
        _receive(client, order_id)
        lot = _lot(client, "VentaBeta")

        listing = client.post(
            "/api/listings",
            json={"lot_id": lot["id"], "quantity": 1, "unit_price_eur_cents": 250},
        )
        assert listing.status_code == 201, listing.text
        listing_id = listing.json()["id"]
        assert listing.json()["status"] == "ACTIVE"

        sold = client.post(
            f"/api/listings/{listing_id}/sell",
            json={"quantity": 1, "unit_price_eur_cents": 250, "fees_eur_cents": 0},
        )
        assert sold.status_code == 200, sold.text

        listings = client.get("/api/listings").json()
        match = next(item for item in listings if item["id"] == listing_id)
        assert match["status"] == "SOLD"
        assert match["quantity"] == 0


def test_sell_over_available_rejected():
    with TestClient(app) as client:
        order_id = _order(client, "VentaGamma", 1)
        _receive(client, order_id)
        lot = _lot(client, "VentaGamma")

        response = client.post(
            f"/api/inventory/{lot['id']}/sell",
            json={"quantity": 2, "unit_price_eur_cents": 100},
        )
        assert response.status_code == 422
