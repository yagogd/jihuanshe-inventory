from app.domain.costs import compute_order_landed
from app.domain.enums import AllocationMethod
from app.domain.models import Order, OrderItem


def _item(raw_name, quantity, unit_price_fen):
    return OrderItem(
        raw_name=raw_name,
        normalized_name=raw_name,
        quantity=quantity,
        unit_price_fen=unit_price_fen,
        include_in_allocation=True,
    )


def _order(items, card_charged=None, fx=0.13, domestic=1000):
    order = Order(
        domestic_shipping_fen=domestic,
        alipay_fee_fen=0,
        fx_cny_eur=fx,
        fx_source="fixed",
        card_charged_eur_cents=card_charged,
        cost_method=AllocationMethod.BY_VALUE,
    )
    for item in items:
        order.items.append(item)
    return order


def test_landed_estimates_without_card_charge():
    order = _order([_item("A", 1, 10000), _item("B", 1, 10000)])
    result = compute_order_landed(order)
    # 21000 fen * 0.13 = 2730
    assert result["total_landed_eur_cents"] == 2730
    assert result["fx_source"] == "fixed"
    assert result["card_charged_eur_cents"] is None


def test_landed_scales_cny_block_to_card_charge():
    order = _order(
        [_item("A", 1, 10000), _item("B", 1, 10000)],
        card_charged=3000,
    )
    result = compute_order_landed(order)
    assert result["card_charged_eur_cents"] == 3000
    # the whole CNY block (purchase + domestic) is scaled to 3000
    assert sum(item["cny_eur_cents"] for item in result["items"]) == 3000
    assert result["total_landed_eur_cents"] == 3000
    # each line carries half (10500 fen each)
    assert result["items"][0]["cny_eur_cents"] == 1500
    assert result["items"][1]["cny_eur_cents"] == 1500
