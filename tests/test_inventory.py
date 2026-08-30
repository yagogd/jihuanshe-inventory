from fastapi.testclient import TestClient

from app.main import app


def _create_order(client: TestClient, name: str, quantity: int) -> str:
    response = client.post(
        "/api/orders",
        json={
            "seller": "s",
            "items": [{"raw_name": name, "quantity": quantity, "unit_price_fen": 1000}],
        },
    )
    assert response.status_code == 201, response.text
    return response.json()["id"]


def _receive(client: TestClient, order_id: str) -> None:
    shipment = client.post("/api/shipments", json={"order_ids": [order_id], "costs": []}).json()
    response = client.post(f"/api/shipments/{shipment['id']}/receive")
    assert response.status_code == 200, response.text


def test_receive_materializes_lot_and_movements():
    with TestClient(app) as client:
        order_id = _create_order(client, "InventarioAlpha", 3)
        _receive(client, order_id)

        lots = client.get("/api/inventory", params={"q": "InventarioAlpha"}).json()
        assert len(lots) == 1
        lot = lots[0]
        assert lot["quantity"] == 3
        assert lot["available"] == 3

        moved = client.post(
            f"/api/inventory/{lot['id']}/movements", json={"kind": "SELL", "quantity": 1}
        )
        assert moved.status_code == 200, moved.text
        assert moved.json()["available"] == 2

        split = client.post(f"/api/inventory/{lot['id']}/split", json={"quantity": 1})
        assert split.status_code == 201, split.text
        assert split.json()["available"] == 1

        all_lots = client.get("/api/inventory", params={"q": "InventarioAlpha"}).json()
        assert len(all_lots) == 2
        assert sorted(lot["available"] for lot in all_lots) == [1, 1]


def test_receive_is_idempotent():
    with TestClient(app) as client:
        order_id = _create_order(client, "InventarioBeta", 2)
        _receive(client, order_id)
        _receive(client, order_id)

        lots = client.get("/api/inventory", params={"q": "InventarioBeta"}).json()
        assert len(lots) == 1
        assert lots[0]["quantity"] == 2


def test_split_and_movement_validation():
    with TestClient(app) as client:
        order_id = _create_order(client, "InventarioGamma", 1)
        _receive(client, order_id)

        lot = client.get("/api/inventory", params={"q": "InventarioGamma"}).json()[0]

        # split needs 1 <= n < available (available == 1 -> no valid split)
        assert client.post(f"/api/inventory/{lot['id']}/split", json={"quantity": 1}).status_code == 422
        assert client.post(f"/api/inventory/{lot['id']}/split", json={"quantity": 0}).status_code == 422

        # movement bigger than available
        assert (
            client.post(
                f"/api/inventory/{lot['id']}/movements", json={"kind": "SELL", "quantity": 2}
            ).status_code
            == 422
        )

        # movement kind RECEIVE is not allowed manually
        assert (
            client.post(
                f"/api/inventory/{lot['id']}/movements", json={"kind": "RECEIVE", "quantity": 1}
            ).status_code
            == 422
        )
