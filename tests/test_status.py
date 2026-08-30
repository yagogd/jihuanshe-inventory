from fastapi.testclient import TestClient

from app.main import app


def _create_order(client: TestClient) -> dict:
    response = client.post(
        "/api/orders",
        json={"seller": "s", "items": [{"raw_name": "carta", "quantity": 1, "unit_price_fen": 100}]},
    )
    assert response.status_code == 201, response.text
    return response.json()


def test_order_status_transition_and_filter():
    with TestClient(app) as client:
        order = _create_order(client)
        assert order["status"] == "PURCHASED"

        updated = client.patch(f"/api/orders/{order['id']}/status", json={"status": "AT_WAREHOUSE"})
        assert updated.status_code == 200, updated.text
        assert updated.json()["status"] == "AT_WAREHOUSE"

        warehouse = client.get("/api/orders", params={"status": "AT_WAREHOUSE"}).json()
        assert any(o["id"] == order["id"] for o in warehouse)

        purchased = client.get("/api/orders", params={"status": "PURCHASED"}).json()
        assert all(o["id"] != order["id"] for o in purchased)

        assert any(o["id"] == order["id"] for o in client.get("/api/orders").json())


def test_order_status_not_found():
    with TestClient(app) as client:
        response = client.patch("/api/orders/missing/status", json={"status": "AT_WAREHOUSE"})
        assert response.status_code == 404
