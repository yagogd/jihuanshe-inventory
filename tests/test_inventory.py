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


def test_manual_add_without_order():
    with TestClient(app) as client:
        created = client.post(
            "/api/inventory",
            json={
                "game": "Pokemon",
                "set_code": "SVP",
                "collector_number": "001",
                "name_zh": "皮卡丘",
                "name_en": "Pikachu",
                "condition": "NM",
                "quantity": 2,
                "amount": 500,
                "currency": "EUR",
                "note": "Cardmarket",
            },
        )
        assert created.status_code == 201, created.text
        lot = created.json()
        assert lot["source"] == "MANUAL"
        assert lot["order_item_id"] is None
        assert lot["available"] == 2
        assert lot["name_en"] == "Pikachu"
        assert lot["unit_cost_eur_cents"] == 250
        assert lot["order_id"] is None

        listing = client.get("/api/inventory", params={"q": "Pikachu"}).json()
        assert len(listing) == 1
        assert listing[0]["source"] == "MANUAL"


def test_manual_add_requires_identity():
    with TestClient(app) as client:
        response = client.post(
            "/api/inventory", json={"name_zh": "Sin set", "quantity": 1, "amount": 100}
        )
        assert response.status_code == 422


def test_update_order_keeps_lots():
    with TestClient(app) as client:
        order_id = _create_order(client, "InventarioDelta", 2)
        _receive(client, order_id)

        order = client.get(f"/api/orders/{order_id}").json()
        item = order["items"][0]
        original_item_id = item["id"]

        payload = {
            "seller": order["seller"],
            "items": [
                {
                    "id": item["id"],
                    "raw_name": "InventarioDelta",
                    "normalized_name": "InventarioDelta editado",
                    "quantity": 2,
                    "unit_price_fen": 1000,
                }
            ],
        }
        updated = client.put(f"/api/orders/{order_id}", json=payload)
        assert updated.status_code == 200, updated.text
        assert updated.json()["items"][0]["id"] == original_item_id

        lots = client.get("/api/inventory", params={"q": "InventarioDelta"}).json()
        assert len(lots) == 1
        assert lots[0]["available"] == 2


def test_inventory_exposes_recalculated_landed_cost_after_shipment_edit():
    with TestClient(app) as client:
        order_id = _create_order(client, "InventarioCosteActual", 1)
        international = next(
            row["id"] for row in client.get("/api/cost-categories").json()
            if row["name"] == "Internacional"
        )
        shipment = client.post(
            "/api/shipments", json={"order_ids": [order_id], "costs": []}
        ).json()
        client.post(f"/api/shipments/{shipment['id']}/receive")

        before = client.get(
            "/api/inventory", params={"q": "InventarioCosteActual"}
        ).json()[0]
        updated = client.put(f"/api/shipments/{shipment['id']}", json={
            "status": "RECEIVED",
            "order_ids": [order_id],
            "total_paid_eur_cents": 500,
            "costs": [{"category_id": international, "amount": 500, "currency": "EUR"}],
        })
        assert updated.status_code == 200, updated.text

        after = client.get(
            "/api/inventory", params={"q": "InventarioCosteActual"}
        ).json()[0]
        assert after["unit_cost_eur_cents"] == before["unit_cost_eur_cents"] + 500


def test_inventory_source_and_foil_filters():
    with TestClient(app) as client:
        client.post(
            "/api/inventory",
            json={
                "game": "Pokemon",
                "set_code": "FILT",
                "collector_number": "007",
                "name_zh": "过滤卡",
                "name_en": "Filter Card",
                "foil": True,
                "quantity": 1,
                "amount": 100,
                "currency": "EUR",
            },
        )

        manual = client.get("/api/inventory", params={"source": "MANUAL", "q": "Filter Card"}).json()
        assert len(manual) == 1
        assert manual[0]["foil"] is True

        received = client.get("/api/inventory", params={"source": "RECEIVE", "q": "Filter Card"}).json()
        assert len(received) == 0

        foil = client.get("/api/inventory", params={"foil": "true", "q": "Filter Card"}).json()
        assert len(foil) == 1


def test_scanned_cards_appear_as_pending():
    with TestClient(app) as client:
        order_id = _create_order(client, "CartaPendiente", 3)

        lots = client.get("/api/inventory", params={"q": "CartaPendiente"}).json()
        assert len(lots) == 1
        assert lots[0]["source"] == "PENDING"
        assert lots[0]["quantity"] == 3
        assert lots[0]["available"] == 0

        # after receiving, it stops being pending
        _receive(client, order_id)
        lots = client.get("/api/inventory", params={"q": "CartaPendiente"}).json()
        assert lots[0]["source"] == "RECEIVE"
        assert lots[0]["available"] == 3


