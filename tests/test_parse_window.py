from pathlib import Path

from app.extractors.uiautomator.parse import parse_window_xml
from app.extractors.uiautomator.parse import _parse_numbering


def test_numbering_discards_decorative_prefix_and_splits_hyphen():
    assert _parse_numbering("·FND-002/298") == ("FND", "002/298")

FIXTURE = Path(__file__).parent / "fixtures" / "window.xml"


def _parse():
    return parse_window_xml(FIXTURE.read_text(encoding="utf-8"))


def test_screen_detected_and_count():
    order = _parse()
    assert order.screen_title == "订单详情"
    assert order.has_product_info is True
    assert order.declared_item_count == 37


def test_truncated_item_discarded():
    order = _parse()
    # Only 4 contentViews exist, the last one (Viktor) is cut off -> 3 complete.
    assert len(order.items) == 3
    assert any("incompleto" in w for w in order.warnings)


def test_first_item_lee_sin():
    item = _parse().items[0]
    assert item.raw_name == "李青, 苦修者"
    assert item.unit_price_fen == 1100
    assert item.quantity == 3
    assert item.set_code == "OGN"
    assert item.collector_number == "078/298"
    assert item.variant == "Promo"
    assert item.promo is True
    assert item.language == "简"
    assert item.game == "符文战场"
    assert item.image_bounds == (84, 1166, 357, 1548)


def test_second_item_ahri():
    item = _parse().items[1]
    assert item.raw_name == "阿狸, 天真绮梦"
    assert item.unit_price_fen == 190
    assert item.quantity == 1
    assert item.variant == "史诗"
    assert item.promo is False


def test_third_item_jinx():
    item = _parse().items[2]
    assert item.raw_name == "金克丝, 反抗者"
    assert item.unit_price_fen == 4450
    assert item.quantity == 3
    assert item.promo is True
