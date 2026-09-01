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


def test_edit_sale_updates_values_and_inventory():
    with TestClient(app) as client:
        order_id = _order(client, "VentaEditable", 3)
        _receive(client, order_id)
        lot = _lot(client, "VentaEditable")
        sale = client.post(
            f"/api/inventory/{lot['id']}/sell",
            json={"quantity": 1, "unit_price_eur_cents": 200, "fees_eur_cents": 10},
        ).json()

        edited = client.put(
            f"/api/sales/{sale['id']}",
            json={"quantity": 2, "unit_price_eur_cents": 250, "fees_eur_cents": 20},
        )
        assert edited.status_code == 200, edited.text
        assert edited.json()["quantity"] == 2
        assert edited.json()["revenue_eur_cents"] == 500
        assert edited.json()["fees_eur_cents"] == 20
        assert _lot(client, "VentaEditable")["available"] == 1

        restored = client.put(
            f"/api/sales/{sale['id']}",
            json={"quantity": 1, "unit_price_eur_cents": 225, "fees_eur_cents": 5},
        )
        assert restored.status_code == 200
        assert _lot(client, "VentaEditable")["available"] == 2


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


def test_sale_marks_other_marketplaces_for_removal_when_stock_runs_out():
    with TestClient(app) as client:
        order_id = _order(client, "VentaMultiMarket", 1)
        _receive(client, order_id)
        lot = _lot(client, "VentaMultiMarket")
        cardmarket = client.post("/api/listings", json={
            "lot_id": lot["id"], "quantity": 1,
            "unit_price_eur_cents": 300, "marketplace": "CARDMARKET",
        }).json()
        client.post("/api/listings", json={
            "lot_id": lot["id"], "quantity": 1,
            "unit_price_eur_cents": 350, "marketplace": "EBAY",
        })

        sold = client.post(f"/api/listings/{cardmarket['id']}/sell", json={
            "quantity": 1, "unit_price_eur_cents": 300, "fees_eur_cents": 0,
        })
        assert sold.status_code == 200, sold.text
        ebay = next(
            row for row in client.get("/api/listings").json()
            if row["lot_id"] == lot["id"] and row["marketplace"] == "EBAY"
        )
        assert ebay["status"] == "NEEDS_REMOVAL"


def test_other_marketplace_stays_active_when_enough_stock_remains():
    with TestClient(app) as client:
        order_id = _order(client, "VentaMultiStock", 2)
        _receive(client, order_id)
        lot = _lot(client, "VentaMultiStock")
        cardmarket = client.post("/api/listings", json={
            "lot_id": lot["id"], "quantity": 1,
            "unit_price_eur_cents": 300, "marketplace": "CARDMARKET",
        }).json()
        client.post("/api/listings", json={
            "lot_id": lot["id"], "quantity": 1,
            "unit_price_eur_cents": 350, "marketplace": "EBAY",
        })
        client.post(f"/api/listings/{cardmarket['id']}/sell", json={
            "quantity": 1, "unit_price_eur_cents": 300, "fees_eur_cents": 0,
        })
        ebay = next(
            row for row in client.get("/api/listings").json()
            if row["lot_id"] == lot["id"] and row["marketplace"] == "EBAY"
        )
        assert ebay["status"] == "ACTIVE"
        assert ebay["available"] == 1


def test_listing_can_be_deleted_completely():
    with TestClient(app) as client:
        order_id = _order(client, "VentaEliminar", 1)
        _receive(client, order_id)
        lot = _lot(client, "VentaEliminar")
        listing = client.post("/api/listings", json={
            "lot_id": lot["id"], "quantity": 1,
            "unit_price_eur_cents": 200, "marketplace": "WALLAPOP",
        }).json()
        deleted = client.delete(f"/api/listings/{listing['id']}")
        assert deleted.status_code == 204, deleted.text
        assert all(
            row["id"] != listing["id"] for row in client.get("/api/listings").json()
        )


def test_active_listing_can_be_edited():
    with TestClient(app) as client:
        order_id = _order(client, "VentaEditar", 3)
        _receive(client, order_id)
        lot = _lot(client, "VentaEditar")
        listing = client.post("/api/listings", json={
            "lot_id": lot["id"], "quantity": 1,
            "unit_price_eur_cents": 200, "marketplace": "WALLAPOP",
        }).json()

        edited = client.put(f"/api/listings/{listing['id']}", json={
            "quantity": 2,
            "unit_price_eur_cents": 275,
            "marketplace": "EBAY",
        })

        assert edited.status_code == 200, edited.text
        assert edited.json()["quantity"] == 2
        assert edited.json()["unit_price_eur_cents"] == 275
        assert edited.json()["marketplace"] == "EBAY"


def _manual_lot(client: TestClient, number: str, name: str, quantity: int = 1) -> dict:
    response = client.post("/api/inventory", json={
        "game": "Test", "set_code": "BND", "collector_number": number,
        "name_en": name, "quantity": quantity, "amount": 100, "currency": "EUR",
    })
    assert response.status_code == 201, response.text
    return response.json()


def test_selling_bundle_consumes_all_cards_and_flags_individual_listings():
    with TestClient(app) as client:
        first = _manual_lot(client, "001", "Bundle One")
        second = _manual_lot(client, "002", "Bundle Two")
        individual = client.post("/api/listings", json={
            "lot_id": first["id"], "quantity": 1,
            "unit_price_eur_cents": 300, "marketplace": "EBAY",
        }).json()
        bundle = client.post("/api/bundles", json={
            "name": "Pack de prueba",
            "items": [{"lot_id": first["id"], "quantity": 1}, {"lot_id": second["id"], "quantity": 1}],
            "listings": [{"marketplace": "CARDMARKET", "unit_price_eur_cents": 700}],
        })
        assert bundle.status_code == 201, bundle.text
        bundle_listing = bundle.json()["listings"][0]

        sold = client.post(f"/api/bundle-listings/{bundle_listing['id']}/sell", json={
            "quantity": 1, "unit_price_eur_cents": 700, "fees_eur_cents": 0,
        })
        assert sold.status_code == 200, sold.text
        assert all(row["available"] == 0 for row in client.get("/api/inventory", params={"set_code": "BND"}).json())
        listing = next(row for row in client.get("/api/listings").json() if row["id"] == individual["id"])
        assert listing["status"] == "NEEDS_REMOVAL"


def test_selling_individual_card_flags_bundle_listing():
    with TestClient(app) as client:
        first = _manual_lot(client, "011", "Bundle Reverse One")
        second = _manual_lot(client, "012", "Bundle Reverse Two")
        bundle = client.post("/api/bundles", json={
            "name": "Pack inverso",
            "items": [{"lot_id": first["id"], "quantity": 1}, {"lot_id": second["id"], "quantity": 1}],
            "listings": [{"marketplace": "EBAY", "unit_price_eur_cents": 800}],
        }).json()
        individual = client.post("/api/listings", json={
            "lot_id": first["id"], "quantity": 1,
            "unit_price_eur_cents": 350, "marketplace": "WALLAPOP",
        }).json()
        client.post(f"/api/listings/{individual['id']}/sell", json={
            "quantity": 1, "unit_price_eur_cents": 350, "fees_eur_cents": 0,
        })
        bundles = client.get("/api/bundles").json()
        listing = next(row for row in bundles[0]["listings"] if row["id"] == bundle["listings"][0]["id"])
        assert listing["status"] == "NEEDS_REMOVAL"
