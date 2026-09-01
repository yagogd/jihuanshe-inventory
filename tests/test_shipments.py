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
                "display_name": "Lote de agosto",
                "order_ids": [o1["id"], o2["id"]],
                "total_paid_eur_cents": 1500,
                "costs": [{"category_id": international, "amount": 1500, "currency": "EUR"}],
            },
        )
        assert created.status_code == 201, created.text
        body = created.json()
        assert body["status"] == "PREPARING"
        assert body["display_name"] == "Lote de agosto"
        assert body["total_paid_eur_cents"] == 1500
        assert len(body["orders"]) == 2
        assert body["costs"][0]["amount_eur_cents"] == 1500

        aduanas = _category_id(client, "Aduanas")
        updated = client.put(
            f"/api/shipments/{body['id']}",
            json={
                "display_name": "Lote principal",
                "status": "SHIPPED",
                "cost_method": "BY_QUANTITY",
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
        assert u["display_name"] == "Lote principal"
        assert len(u["orders"]) == 1
        assert u["orders"][0]["id"] == o1["id"]
        assert len(u["costs"]) == 2

        listing = client.get("/api/shipments").json()
        assert any(s["id"] == body["id"] for s in listing)

        detail = client.get(f"/api/shipments/{body['id']}").json()
        assert detail["id"] == body["id"]
        assert detail["status"] == "SHIPPED"
        assert detail["total_paid_eur_cents"] == 2500
        assert detail["cost_method"] == "BY_QUANTITY"
        assert all(cost["method"] == "BY_QUANTITY" for cost in detail["costs"])


def test_delete_shipment_preserves_and_unlinks_orders():
    with TestClient(app) as client:
        order = _order(client)
        shipment = client.post(
            "/api/shipments",
            json={"display_name": "Temporal", "order_ids": [order["id"]], "costs": []},
        ).json()

        deleted = client.delete(f"/api/shipments/{shipment['id']}")
        assert deleted.status_code == 204, deleted.text
        assert client.get(f"/api/shipments/{shipment['id']}").status_code == 404
        assert client.get(f"/api/orders/{order['id']}").status_code == 200


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


def test_received_shipment_costs_can_be_edited_and_persisted():
    with TestClient(app) as client:
        order = _order(client)
        international = _category_id(client, "Internacional")
        created = client.post(
            "/api/shipments",
            json={"order_ids": [order["id"]], "total_paid_eur_cents": 0, "costs": []},
        ).json()
        received = client.post(f"/api/shipments/{created['id']}/receive")
        assert received.status_code == 200, received.text

        updated = client.put(
            f"/api/shipments/{created['id']}",
            json={
                "status": "RECEIVED",
                "order_ids": [order["id"]],
                "total_paid_eur_cents": 7100,
                "cost_method": "BY_QUANTITY",
                "costs": [
                    {"category_id": international, "amount": 7100, "currency": "EUR"}
                ],
            },
        )
        assert updated.status_code == 200, updated.text

        detail = client.get(f"/api/shipments/{created['id']}").json()
        assert detail["status"] == "RECEIVED"
        assert detail["total_paid_eur_cents"] == 7100
        assert detail["cost_method"] == "BY_QUANTITY"
        assert detail["costs"][0]["amount"] == 7100


def test_setting_shipment_status_to_received_materializes_inventory():
    with TestClient(app) as client:
        order = _order(client)
        created = client.post(
            "/api/shipments",
            json={"order_ids": [order["id"]], "total_paid_eur_cents": 0, "costs": []},
        ).json()

        updated = client.put(
            f"/api/shipments/{created['id']}",
            json={
                "status": "RECEIVED",
                "order_ids": [order["id"]],
                "total_paid_eur_cents": 0,
                "costs": [],
            },
        )
        assert updated.status_code == 200, updated.text

        inventory = client.get("/api/inventory", params={"q": "carta"}).json()
        received = [
            row for row in inventory
            if row["source"] == "RECEIVE"
            and row["order_item_id"] == order["items"][0]["id"]
        ]
        assert len(received) == 1
        assert received[0]["available"] == 1

        # Saving RECEIVED again must not duplicate its inventory lot.
        repeated = client.put(
            f"/api/shipments/{created['id']}",
            json={
                "status": "RECEIVED",
                "order_ids": [order["id"]],
                "total_paid_eur_cents": 0,
                "costs": [],
            },
        )
        assert repeated.status_code == 200, repeated.text
        inventory = client.get("/api/inventory", params={"q": "carta"}).json()
        assert len([
            row for row in inventory
            if row["source"] == "RECEIVE"
            and row["order_item_id"] == order["items"][0]["id"]
        ]) == 1


def test_receiving_shipment_stores_purchase_plus_shipping_unit_cost():
    with TestClient(app) as client:
        order = _order(client)  # 1 unit at 1.00 CNY; default FX 0.13 => 0.13 EUR
        international = _category_id(client, "Internacional")
        created = client.post(
            "/api/shipments",
            json={
                "order_ids": [order["id"]],
                "total_paid_eur_cents": 100,
                "costs": [
                    {"category_id": international, "amount": 100, "currency": "EUR"}
                ],
            },
        ).json()

        received = client.post(f"/api/shipments/{created['id']}/receive")
        assert received.status_code == 200, received.text

        inventory = client.get("/api/inventory", params={"q": "carta"}).json()
        lot = next(
            row for row in inventory
            if row["source"] == "RECEIVE"
            and row["order_item_id"] == order["items"][0]["id"]
        )
        expected_purchase_cents = round(100 * order["fx_cny_eur"])
        assert lot["unit_cost_eur_cents"] == expected_purchase_cents + 100


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
