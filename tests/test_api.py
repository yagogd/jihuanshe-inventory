from fastapi.testclient import TestClient

from app.config import get_settings
from app.deps import get_extractor
from app.extractors.contract import CapturePreview, CaptureStatus, ParsedItem, ParsedOrder
from app.extractors.session import start_session
from app.main import app

_ITEM_XML = (
    '<hierarchy><node package="com.jihuanshe" text="" resource-id="">'
    '<node text="订单详情" resource-id=""/>'
    '<node resource-id="com.jihuanshe:id/tvNum" text="1"/>'
    '<node resource-id="com.jihuanshe:id/contentView" text="">'
    '<node resource-id="com.jihuanshe:id/officialNameTv" text="卡A"/>'
    '<node resource-id="com.jihuanshe:id/priceView" text="11"/>'
    '<node resource-id="com.jihuanshe:id/tv_num" text="x2"/>'
    '</node></node></hierarchy>'
)


class FakeExtractor:
    def status(self):
        return CaptureStatus(
            detected=True, available=True, screen_title="订单详情", declared_item_count=2
        )

    def preview(self, auto_scroll=False):
        order = ParsedOrder(
            screen_title="订单详情",
            declared_item_count=2,
            items=[
                ParsedItem(
                    raw_name="卡A",
                    quantity=2,
                    unit_price_fen=1100,
                    set_code="OGN",
                    collector_number="078/298",
                    variant="Promo",
                    promo=True,
                    language="简",
                )
            ],
        )
        return CapturePreview(
            detected=True,
            session_id="sess1",
            screen_title="订单详情",
            declared_item_count=2,
            order=order,
            raw_dumps=["<hierarchy/>"],
            warnings=[],
        )

    def new_session(self):
        return start_session(get_settings())

    def capture_current(self):
        return _ITEM_XML, None


def test_health():
    with TestClient(app) as client:
        response = client.get("/api/health")
        assert response.status_code == 200
        assert response.json()["status"] == "ok"


def test_import_status_detected():
    app.dependency_overrides[get_extractor] = lambda: FakeExtractor()
    try:
        with TestClient(app) as client:
            body = client.get("/api/import/status").json()
            assert body["available"] is True
            assert body["detected"] is True
            assert body["declared_item_count"] == 2
    finally:
        app.dependency_overrides.clear()


def test_import_preview_and_create_order():
    app.dependency_overrides[get_extractor] = lambda: FakeExtractor()
    try:
        with TestClient(app) as client:
            preview = client.post("/api/import/preview").json()
            assert preview["detected"] is True
            assert preview["subtotal_fen"] == 2200
            assert preview["items"][0]["raw_name"] == "卡A"

            payload = {
                "seller": "测试卖家",
                "purchase_date": "2026-08-06",
                "domestic_shipping_fen": 800,
                "fx_cny_eur": 0.13,
                "items": preview["items"],
                "session_id": preview["session_id"],
                "raw_dumps": preview["raw_dumps"],
                "warnings": preview["warnings"],
                "declared_item_count": preview["declared_item_count"],
            }
            response = client.post("/api/orders", json=payload)
            assert response.status_code == 201, response.text
            body = response.json()

            # subtotal 2200 + domestic 800 = 3000 fen (30.00 yuan) <= 200 -> no fee
            assert body["seller"] == "测试卖家"
            assert body["subtotal_fen"] == 2200
            assert body["domestic_shipping_fen"] == 800
            assert body["alipay_fee_fen"] == 0
            assert body["total_paid_fen"] == 3000
            assert len(body["items"]) == 1

            listing = client.get("/api/orders").json()
            assert len(listing) == 1

            detail = client.get(f"/api/orders/{body['id']}").json()
            assert detail["id"] == body["id"]
            assert detail["items"][0]["raw_name"] == "卡A"
            assert detail["seller"] == "测试卖家"
            assert detail["domestic_shipping_fen"] == 800

            payload["seller"] = "Vendedor editado"
            payload["items"][0]["quantity"] = 3
            payload["total_paid_fen"] = None
            updated = client.put(f"/api/orders/{body['id']}", json=payload)
            assert updated.status_code == 200, updated.text
            assert updated.json()["seller"] == "Vendedor editado"
            assert updated.json()["items"][0]["quantity"] == 3
    finally:
        app.dependency_overrides.clear()
