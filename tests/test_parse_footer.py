from pathlib import Path

from app.extractors.uiautomator.parse import parse_window_xml

FIXTURE = Path(__file__).parent / "fixtures" / "window_footer.xml"


def test_footer_money():
    order = parse_window_xml(FIXTURE.read_text(encoding="utf-8"))
    assert order.domestic_shipping_fen == 1800  # 18元
    assert order.subtotal_fen == 102500  # 1025元
    assert order.total_paid_fen == 104300  # ¥1043
    assert order.reached_footer is True


def test_footer_items_and_prices():
    order = parse_window_xml(FIXTURE.read_text(encoding="utf-8"))
    prices = {item.raw_name: item.unit_price_fen for item in order.items}
    assert prices["厄运小姐（试玩版）"] == 45000
    assert prices["维克托（试玩版）"] == 10000
    assert prices["狂风绝息斩（试玩版）"] == 3000
    assert all(item.quantity == 1 for item in order.items)
