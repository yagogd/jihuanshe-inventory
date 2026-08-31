import xml.etree.ElementTree as ET

from app.config import Settings
from app.extractors.uiautomator.extractor import UIAutomatorExtractor


class FakeAdb:
    """Simulates a phone screen list (top -> bottom) with a movable cursor."""

    def __init__(self, screens, start=0):
        self.screens = screens
        self.cursor = start
        self.swipes_up = 0
        self.swipes_down = 0

    def available(self):
        return True

    def current_window_xml(self):
        if not self.screens:
            return None
        self.cursor = max(0, min(self.cursor, len(self.screens) - 1))
        return self.screens[self.cursor]

    def screenshot_bytes(self):
        return None

    def swipe_up(self):
        self.swipes_up += 1
        self.cursor = min(self.cursor + 1, len(self.screens) - 1)

    def swipe_down(self):
        self.swipes_down += 1
        self.cursor = max(self.cursor - 1, 0)


def _item(name, num, price="10", qty="x1", precious="Promo"):
    cv = ET.Element("node", {"resource-id": "com.jihuanshe:id/contentView", "text": ""})
    ET.SubElement(cv, "node", {"resource-id": "com.jihuanshe:id/officialNameTv", "text": name})
    ET.SubElement(cv, "node", {"resource-id": "com.jihuanshe:id/priceView", "text": price})
    ET.SubElement(cv, "node", {"resource-id": "com.jihuanshe:id/tv_num", "text": qty})
    ET.SubElement(
        cv, "node", {"resource-id": "com.jihuanshe:id/tv_numbering", "text": f"SET·{num}"}
    )
    ET.SubElement(cv, "node", {"resource-id": "com.jihuanshe:id/tv_preciousness", "text": precious})
    return cv


def _header_dump(seller="卖家X", order_id="20260001", company="顺丰速运", tracking="SF1575562409202"):
    root = ET.Element("hierarchy")
    top = ET.SubElement(root, "node", {"package": "com.jihuanshe", "text": "", "resource-id": ""})
    ET.SubElement(top, "node", {"text": "订单详情", "resource-id": ""})
    ET.SubElement(top, "node", {"resource-id": "com.jihuanshe:id/sellerNameTv", "text": "卖家姓名："})
    ET.SubElement(top, "node", {"text": seller, "resource-id": ""})
    ET.SubElement(top, "node", {"resource-id": "com.jihuanshe:id/orderNumTv", "text": "订单编号："})
    ET.SubElement(top, "node", {"text": order_id, "resource-id": ""})
    ET.SubElement(top, "node", {"resource-id": "com.jihuanshe:id/orderTimeTv", "text": "交易时间："})
    ET.SubElement(top, "node", {"text": "2026-08-04 00:06:34", "resource-id": ""})
    express = ET.SubElement(
        top, "node", {"resource-id": "com.jihuanshe:id/expressContent", "text": ""}
    )
    ET.SubElement(express, "node", {"text": company, "resource-id": ""})
    ET.SubElement(express, "node", {"text": tracking, "resource-id": ""})
    return ET.tostring(root, encoding="utf-8").decode("utf-8")


def _items_dump(items, declared):
    root = ET.Element("hierarchy")
    top = ET.SubElement(root, "node", {"package": "com.jihuanshe", "text": "", "resource-id": ""})
    ET.SubElement(top, "node", {"text": "订单详情", "resource-id": ""})
    ET.SubElement(top, "node", {"resource-id": "com.jihuanshe:id/tvNum", "text": str(declared)})
    for item in items:
        top.append(item)
    return ET.tostring(root, encoding="utf-8").decode("utf-8")


def _footer_dump(shipping="18元", products="1025元", total="1043"):
    root = ET.Element("hierarchy")
    top = ET.SubElement(root, "node", {"package": "com.jihuanshe", "text": "", "resource-id": ""})
    ET.SubElement(top, "node", {"text": "订单详情", "resource-id": ""})
    ship = ET.SubElement(top, "node", {"resource-id": "com.jihuanshe:id/llShipping", "text": ""})
    ET.SubElement(ship, "node", {"text": "邮费", "resource-id": ""})
    ET.SubElement(ship, "node", {"text": shipping, "resource-id": ""})
    price = ET.SubElement(
        top, "node", {"resource-id": "com.jihuanshe:id/llProductsPrice", "text": ""}
    )
    ET.SubElement(price, "node", {"text": "商品总价", "resource-id": ""})
    ET.SubElement(price, "node", {"text": products, "resource-id": ""})
    ET.SubElement(top, "node", {"text": "实付款", "resource-id": ""})
    ET.SubElement(top, "node", {"resource-id": "com.jihuanshe:id/priceView", "text": total})
    return ET.tostring(root, encoding="utf-8").decode("utf-8")


def _settings(tmp_path):
    return Settings(
        adb_path="adb",
        data_dir=tmp_path,
        alipay_fee_threshold_fen=20000,
        alipay_fee_rate=0.03,
        fx_cny_eur=0.13,
        capture_images=False,
        max_scrolls=80,
        auto_translate=False,
    )


def test_full_scroll_captures_header_items_and_footer(tmp_path):
    a = [_item("A", "001"), _item("B", "002"), _item("C", "003")]
    b = [_item("B", "002"), _item("C", "003"), _item("D", "004"), _item("E", "005")]
    screens = [
        _header_dump(),
        _items_dump(a, declared=5),
        _items_dump(b, declared=5),
        _footer_dump(),
    ]
    extractor = UIAutomatorExtractor(FakeAdb(screens), _settings(tmp_path))
    preview = extractor.preview(auto_scroll=True)

    assert preview.detected is True
    assert preview.order.seller == "卖家X"
    assert preview.order.jihuanshe_order_id == "20260001"
    assert preview.order.express_company == "顺丰速运"
    assert preview.order.express_tracking == "SF1575562409202"
    assert [i.raw_name for i in preview.order.items] == ["A", "B", "C", "D", "E"]
    assert preview.order.domestic_shipping_fen == 1800
    assert preview.order.subtotal_fen == 102500
    assert preview.order.total_paid_fen == 104300
    assert preview.order.reached_footer is True


def test_capture_from_middle_seeks_header_and_footer(tmp_path):
    a = [_item("A", "001"), _item("B", "002")]
    screens = [
        _header_dump(seller="卖家Y", order_id="20260002"),
        _items_dump(a, declared=2),
        _footer_dump(),
    ]
    extractor = UIAutomatorExtractor(FakeAdb(screens, start=1), _settings(tmp_path))
    preview = extractor.preview(auto_scroll=True)
    assert preview.order.seller == "卖家Y"
    assert preview.order.jihuanshe_order_id == "20260002"
    assert preview.order.purchase_date == "2026-08-04 00:06:34"
    assert preview.order.express_company == "顺丰速运"
    assert preview.order.express_tracking == "SF1575562409202"
    assert [i.raw_name for i in preview.order.items] == ["A", "B"]
    assert preview.order.reached_footer is True


def test_stuck_stops_without_footer(tmp_path):
    a = [_item("A", "001"), _item("B", "002")]
    screens = [_header_dump(), _items_dump(a, declared=2)]
    extractor = UIAutomatorExtractor(FakeAdb(screens), _settings(tmp_path))
    preview = extractor.preview(auto_scroll=True)
    assert [i.raw_name for i in preview.order.items] == ["A", "B"]
    assert any("sin progreso" in w for w in preview.warnings)
