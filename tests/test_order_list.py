from types import SimpleNamespace

from fastapi.testclient import TestClient

from app.deps import get_extractor
from app.extractors.contract import CapturePreview, ListedOrder, ParsedItem, ParsedOrder
from app.extractors.uiautomator.order_list import parse_order_list
from app.main import app


def test_parse_visible_orders_and_cancelled_state():
    xml = """<hierarchy><node clickable="false">
      <node clickable="true" bounds="[21,100][1251,900]">
        <node resource-id="com.jihuanshe:id/userNameTv"><node text="Seller"/></node>
        <node resource-id="com.jihuanshe:id/stateTv" text="订单已取消"/>
        <node resource-id="com.jihuanshe:id/orderNumTv" text="20260001"/>
      </node>
      <node clickable="true" bounds="[21,925][1251,1200]">
        <node resource-id="com.jihuanshe:id/stateTv" text="已完成"/>
      </node>
    </node></hierarchy>"""
    orders = parse_order_list(xml)
    assert len(orders) == 1
    assert orders[0].jihuanshe_order_id == "20260001"
    assert orders[0].seller == "Seller"
    assert orders[0].cancelled is True


class FakeBulkExtractor:
    settings = SimpleNamespace(max_scrolls=8)

    def __init__(self):
        self.orders = [
            ListedOrder("NEW-1", "已完成", "Seller", (20, 100, 1200, 800)),
            ListedOrder("CANCEL-1", "订单已取消", "Other", (20, 825, 1200, 1500)),
        ]

    def visible_listed_orders(self):
        return self.orders

    def open_listed_order(self, _order):
        return True

    def preview(self, auto_scroll=False):
        assert auto_scroll is True
        return CapturePreview(
            detected=True,
            session_id=None,
            screen_title="订单详情",
            declared_item_count=1,
            order=ParsedOrder(
                screen_title="订单详情",
                has_product_info=True,
                jihuanshe_order_id="NEW-1",
                seller="Seller",
                items=[ParsedItem(raw_name="Card", unit_price_fen=100)],
            ),
        )

    def return_to_order_list(self):
        return True

    def scroll_order_list(self):
        pass


def test_bulk_import_saves_new_and_skips_cancelled():
    fake = FakeBulkExtractor()
    app.dependency_overrides[get_extractor] = lambda: fake
    try:
        with TestClient(app) as client:
            response = client.post("/api/import/bulk")
            assert response.status_code == 200, response.text
            body = response.json()
            assert body["imported"] == 1
            assert body["cancelled"] == 1
            assert body["failed"] == 0
            assert body["reached_end"] is True
            imported = next(item for item in body["items"] if item["status"] == "imported")
            assert imported["order_id"] is not None
            assert client.get("/api/orders").json()[0]["jihuanshe_order_id"] == "NEW-1"

            repeated = client.post("/api/import/bulk").json()
            registered = next(
                item for item in repeated["items"] if item["status"] == "already_registered"
            )
            assert registered["order_id"] == imported["order_id"]
    finally:
        app.dependency_overrides.clear()
