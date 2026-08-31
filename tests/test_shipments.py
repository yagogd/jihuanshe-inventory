from fastapi.testclient import TestClient

from app.main import app


def _order(client: TestClient) -> dict:
    response = client.post(
        "/api/orders",
        json={"seller": "s", "items": [{"raw_name": "carta", "quantity": 1, "unit_price_fen": 100}]},
    )
    assert response.status_code == 201, response.text
    return response.json()


def _category_id(client: TestClient, name: str) -> str:
    categories = client.get("/api/cost-categories").json()
    return next(c["id"] for c in categories if c["name"] == name)


def test_shipment_create_and_assign():
    with TestClient(app) as client:
        o1 = _order(client)
        o2 = _order(client)
        international = _category_id(client, "Internacional")

        created = client.post(
            "/api/shipments",
            json={
                "order_ids": [o1["id"], o2["id"]],
                "total_paid_eur_cents": 1500,
                "costs": [{"category_id": international, "amount": 1500, "currency": "EUR"}],
            },
        )
        assert created.status_code == 201, created.text
        body = created.json()
        assert body["status"] == "PREPARING"
        assert body["total_paid_eur_cents"] == 1500
        assert len(body["orders"]) == 2
        assert body["costs"][0]["amount_eur_cents"] == 1500

        aduanas = _category_id(client, "Aduanas")
        updated = client.put(
            f"/api/shipments/{body['id']}",
            json={
                "status": "SHIPPED",
                "order_ids": [o1["id"]],
                "total_paid_eur_cents": 2500,
                "costs": [
                    {"category_id": international, "amount": 2000, "currency": "EUR"},
                    {"category_id": aduanas, "amount": 500, "currency": "EUR"},
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


def test_shipment_rejects_mismatched_breakdown():
    with TestClient(app) as client:
        o1 = _order(client)
        international = _category_id(client, "Internacional")

        response = client.post(
            "/api/shipments",
            json={
                "order_ids": [o1["id"]],
                "total_paid_eur_cents": 2000,
                "costs": [{"category_id": international, "amount": 1500, "currency": "EUR"}],
            },
        )
        assert response.status_code == 422
        assert "suma" in response.json()["detail"]


def test_shipment_not_found():
    with TestClient(app) as client:
        assert client.get("/api/shipments/missing").status_code == 404


def test_create_custom_category():
    with TestClient(app) as client:
        created = client.post(
            "/api/cost-categories", json={"name": "Protección esquinas", "kind": "custom"}
        )
        assert created.status_code == 201, created.text
        assert created.json()["name"] == "Protección esquinas"

        again = client.post(
            "/api/cost-categories", json={"name": "Protección esquinas", "kind": "custom"}
        )
        assert again.status_code == 201
        assert again.json()["id"] == created.json()["id"]
