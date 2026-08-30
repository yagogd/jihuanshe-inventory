from fastapi.testclient import TestClient

from app.main import app


def _order(client: TestClient) -> dict:
    response = client.post(
        "/api/orders",
        json={"seller": "s", "items": [{"raw_name": "carta", "quantity": 1, "unit_price_fen": 100}]},
    )
    assert response.status_code == 201, response.text
    return response.json()


def test_shipment_create_and_assign():
    with TestClient(app) as client:
        o1 = _order(client)
        o2 = _order(client)

        created = client.post(
            "/api/shipments",
            json={
                "order_ids": [o1["id"], o2["id"]],
                "costs": [{"type": "INTERNATIONAL", "amount_eur_cents": 1500}],
            },
        )
        assert created.status_code == 201, created.text
        body = created.json()
        assert body["status"] == "PREPARING"
        assert len(body["orders"]) == 2
        assert body["costs"][0]["amount_eur_cents"] == 1500

        updated = client.put(
            f"/api/shipments/{body['id']}",
            json={
                "status": "SHIPPED",
                "order_ids": [o1["id"]],
                "costs": [
                    {"type": "INTERNATIONAL", "amount_eur_cents": 2000},
                    {"type": "CUSTOMS", "amount_eur_cents": 500},
                ],
            },
        )
        assert updated.status_code == 200, updated.text
        u = updated.json()
        assert u["status"] == "SHIPPED"
        assert len(u["orders"]) == 1
        assert u["orders"][0]["id"] == o1["id"]
        assert len(u["costs"]) == 2

        listing = client.get("/api/shipments").json()
        assert any(s["id"] == body["id"] for s in listing)

        detail = client.get(f"/api/shipments/{body['id']}").json()
        assert detail["id"] == body["id"]


def test_shipment_not_found():
    with TestClient(app) as client:
        assert client.get("/api/shipments/missing").status_code == 404
