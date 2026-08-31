from fastapi.testclient import TestClient

from app.domain.costs import allocate_largest_remainder, compute_order_landed
from app.domain.enums import AllocationMethod, CostCategoryKind, Currency, ShipmentStatus
from app.domain.models import CostCategory, Order, OrderItem, Shipment, ShipmentCost
from app.main import app


def test_allocate_even_split():
    assert allocate_largest_remainder([1, 1, 1], 10) == [4, 3, 3]
    assert sum(allocate_largest_remainder([1, 1, 1], 10)) == 10


def test_allocate_exact_proportions():
    assert allocate_largest_remainder([3, 1], 100) == [75, 25]


def test_allocate_remainder_to_largest_fraction():
    # 1/3 and 2/3 of 1 -> remainder goes to the 2/3 share.
    assert allocate_largest_remainder([1, 2], 1) == [0, 1]


def test_allocate_zero_total():
    assert allocate_largest_remainder([5, 5], 0) == [0, 0]


def test_allocate_zero_weights():
    assert allocate_largest_remainder([0, 0], 100) == [0, 0]


def _item(raw_name, quantity, unit_price_fen, include=True):
    return OrderItem(
        raw_name=raw_name,
        normalized_name=raw_name,
        quantity=quantity,
        unit_price_fen=unit_price_fen,
        include_in_allocation=include,
    )


def _order(items, domestic=0, alipay=0, fx=0.13, method=AllocationMethod.BY_VALUE):
    order = Order(
        domestic_shipping_fen=domestic,
        alipay_fee_fen=alipay,
        fx_cny_eur=fx,
        cost_method=method,
    )
    for item in items:
        order.items.append(item)
    return order


def test_landed_without_shipment():
    order = _order(
        [_item("A", 1, 10000), _item("B", 1, 10000)],
        domestic=1000,
        fx=0.13,
    )
    result = compute_order_landed(order)
    assert result["total_landed_eur_cents"] == 2730
    a, b = result["items"]
    assert a["domestic_cny_fen"] == 500
    assert a["cny_total_fen"] == 10500
    assert a["cny_eur_cents"] == 1365
    assert b["domestic_cny_fen"] == 500


def test_landed_gift_by_value_gets_no_shipping():
    order = _order([_item("gift", 1, 0), _item("card", 1, 10000)], domestic=1000, fx=0.13)
    result = compute_order_landed(order)
    gift, card = result["items"]
    assert gift["domestic_cny_fen"] == 0
    assert card["domestic_cny_fen"] == 1000


def test_landed_gift_by_quantity_carries_shipping():
    order = _order(
        [_item("gift", 1, 0), _item("card", 1, 10000)],
        domestic=1000,
        fx=0.13,
        method=AllocationMethod.BY_QUANTITY,
    )
    result = compute_order_landed(order)
    gift, card = result["items"]
    assert gift["domestic_cny_fen"] == 500
    assert card["domestic_cny_fen"] == 500


def test_landed_with_shipment_costs():
    o1 = _order([_item("A", 1, 10000)], fx=0.13)
    o2 = _order([_item("B", 1, 10000)], fx=0.13)
    shipment = Shipment(status=ShipmentStatus.PREPARING)
    shipment.orders.append(o1)
    shipment.orders.append(o2)
    category = CostCategory(name="Internacional", kind=CostCategoryKind.SHIPPING)
    shipment.costs.append(
        ShipmentCost(
            category=category,
            amount=200,
            currency=Currency.EUR,
            method=AllocationMethod.BY_QUANTITY,
        )
    )

    result = compute_order_landed(o1, shipment)
    assert result["items"][0]["shipment_alloc_cents"]["Internacional"] == 100
    assert result["items"][0]["cny_eur_cents"] == 1300
    assert result["items"][0]["landed_eur_cents"] == 1400
    assert result["total_landed_eur_cents"] == 1400


def test_landed_endpoint():
    with TestClient(app) as client:
        created = client.post(
            "/api/orders",
            json={
                "seller": "s",
                "domestic_shipping_fen": 1000,
                "alipay_fee_fen": 0,
                "fx_cny_eur": 0.13,
                "items": [
                    {"raw_name": "A", "quantity": 1, "unit_price_fen": 10000},
                    {"raw_name": "B", "quantity": 1, "unit_price_fen": 10000},
                ],
            },
        )
        assert created.status_code == 201, created.text
        order_id = created.json()["id"]

        landed = client.get(f"/api/orders/{order_id}/landed").json()
        assert landed["total_landed_eur_cents"] == 2730
        assert len(landed["items"]) == 2
