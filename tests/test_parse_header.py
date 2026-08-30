from pathlib import Path

from app.extractors.uiautomator.parse import parse_window_xml

FIXTURE = Path(__file__).parent / "fixtures" / "window_header.xml"


def test_header_fields_extracted():
    order = parse_window_xml(FIXTURE.read_text(encoding="utf-8"))
    assert order.screen_title == "订单详情"
    assert order.seller == "玩具坑keng"
    assert order.jihuanshe_order_id == "202608040006343672"
    assert order.purchase_date == "2026-08-04 00:06:34"
    assert order.express_company == "顺丰速运"
    assert order.express_tracking == "SF1575562409202"


def test_header_screen_has_no_products():
    order = parse_window_xml(FIXTURE.read_text(encoding="utf-8"))
    # Header screen: product list not yet loaded.
    assert order.declared_item_count is None
    assert order.items == []
