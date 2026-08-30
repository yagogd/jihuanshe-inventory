"""Pydantic schemas for the API boundary."""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.domain.enums import ItemOrigin, OrderStatus


class OrderItemIn(BaseModel):
    external_card_id: str | None = None
    raw_name: str
    normalized_name: str | None = None
    game: str | None = None
    set_code: str | None = None
    collector_number: str | None = None
    language: str | None = None
    condition: str | None = None
    variant: str | None = None
    promo: bool = False
    foil: bool = False
    quantity: int = 1
    unit_price_fen: int = 0
    origin: ItemOrigin = ItemOrigin.SCRAPED
    include_in_allocation: bool = True
    image_path: str | None = None
    position: int = 0


class OrderItemOut(OrderItemIn):
    model_config = ConfigDict(from_attributes=True)

    id: str
    normalized_name: str


class OrderIn(BaseModel):
    jihuanshe_order_id: str | None = None
    seller: str | None = None
    purchase_date: str | None = None
    express_company: str | None = None
    express_tracking: str | None = None
    domestic_shipping_fen: int | None = None
    alipay_fee_fen: int | None = None
    total_paid_fen: int | None = None
    fx_cny_eur: float | None = None
    fx_source: str | None = None
    items: list[OrderItemIn]
    session_id: str | None = None
    raw_dumps: list[str] = []
    warnings: list[str] = []
    declared_item_count: int | None = None


class OrderOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    jihuanshe_order_id: str | None
    seller: str | None
    purchase_date: str | None
    express_company: str | None
    express_tracking: str | None
    subtotal_fen: int
    domestic_shipping_fen: int
    alipay_fee_fen: int | None
    total_paid_fen: int
    fx_cny_eur: float
    fx_source: str
    status: OrderStatus
    items: list[OrderItemOut]
    created_at: datetime


class SettingsOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    alipay_fee_threshold_fen: int
    alipay_fee_rate: float
    fx_cny_eur: float


class SettingsIn(BaseModel):
    alipay_fee_threshold_fen: int | None = None
    alipay_fee_rate: float | None = None
    fx_cny_eur: float | None = None


class ImportStatusOut(BaseModel):
    available: bool
    detected: bool
    screen_title: str | None = None
    declared_item_count: int | None = None
    error: str | None = None


class ImportPreviewOut(BaseModel):
    detected: bool
    session_id: str | None = None
    screen_title: str | None = None
    declared_item_count: int | None = None
    jihuanshe_order_id: str | None = None
    seller: str | None = None
    purchase_date: str | None = None
    express_company: str | None = None
    express_tracking: str | None = None
    subtotal_fen: int = 0
    declared_subtotal_fen: int | None = None
    domestic_shipping_fen: int | None = None
    declared_total_paid_fen: int | None = None
    suggested_alipay_fee_fen: int = 0
    fx_cny_eur: float = 0.13
    items: list[OrderItemIn] = []
    raw_dumps: list[str] = []
    warnings: list[str] = []
    error: str | None = None
