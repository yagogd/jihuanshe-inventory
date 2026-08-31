"""Pydantic schemas for the API boundary."""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.domain.enums import (
    AllocationMethod,
    Currency,
    ItemOrigin,
    ListingStatus,
    MovementKind,
    OrderStatus,
    ShipmentStatus,
)


class OrderItemIn(BaseModel):
    id: str | None = None
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
    name_en: str | None = None


class OrderIn(BaseModel):
    jihuanshe_order_id: str | None = None
    display_name: str | None = None
    seller: str | None = None
    purchase_date: str | None = None
    express_company: str | None = None
    express_tracking: str | None = None
    domestic_shipping_fen: int | None = None
    alipay_fee_fen: int | None = None
    total_paid_fen: int | None = None
    fx_cny_eur: float | None = None
    fx_source: str | None = None
    card_charged_eur_cents: int | None = None
    cost_method: AllocationMethod | None = None
    items: list[OrderItemIn]
    session_id: str | None = None
    raw_dumps: list[str] = []
    warnings: list[str] = []
    declared_item_count: int | None = None


class OrderOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    jihuanshe_order_id: str | None
    display_name: str | None
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
    card_charged_eur_cents: int | None
    cost_method: AllocationMethod
    status: OrderStatus
    items: list[OrderItemOut]
    created_at: datetime
    has_sales: bool = False


class SettingsOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    alipay_fee_threshold_fen: int
    alipay_fee_rate: float
    fx_cny_eur: float
    fx_mode: str


class SettingsIn(BaseModel):
    alipay_fee_threshold_fen: int | None = None
    alipay_fee_rate: float | None = None
    fx_cny_eur: float | None = None
    fx_mode: str | None = None


class OrderStatusIn(BaseModel):
    status: OrderStatus


class ShipmentCostIn(BaseModel):
    category_id: str
    amount: int = 0
    currency: Currency = Currency.EUR
    method: AllocationMethod = AllocationMethod.BY_VALUE
    insured_amount: int | None = None
    insured_currency: Currency | None = None


class ShipmentCostOut(ShipmentCostIn):
    model_config = ConfigDict(from_attributes=True)

    id: str
    category_name: str = ""
    category_kind: str = ""
    amount_eur_cents: int = 0


class ShipmentIn(BaseModel):
    status: ShipmentStatus | None = None
    order_ids: list[str] = []
    total_paid_eur_cents: int = 0
    fx_cny_eur: float | None = None
    fx_source: str | None = None
    costs: list[ShipmentCostIn] = []


class ShipmentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    status: ShipmentStatus
    total_paid_eur_cents: int
    fx_cny_eur: float
    fx_source: str
    created_at: datetime
    costs: list[ShipmentCostOut]
    orders: list[OrderOut]
    has_sales: bool = False


class CostCategoryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    kind: str
    position: int


class CostCategoryIn(BaseModel):
    name: str
    kind: str = "custom"


class LandedItemOut(BaseModel):
    item_id: str
    name: str
    quantity: int
    purchase_cny_fen: int
    domestic_cny_fen: int
    alipay_cny_fen: int
    cny_total_fen: int
    cny_eur_cents: int
    shipment_alloc_cents: dict[str, int]
    shipment_eur_cents: int
    landed_eur_cents: int


class LandedOut(BaseModel):
    order_id: str
    fx_cny_eur: float
    fx_source: str
    card_charged_eur_cents: int | None
    items: list[LandedItemOut]
    total_landed_eur_cents: int


class MovementOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    kind: MovementKind
    delta: int
    created_at: datetime


class InventoryLotOut(BaseModel):
    id: str
    order_item_id: str | None
    card_id: str | None
    source: str
    name: str
    name_en: str | None = None
    raw_name: str | None = None
    game: str | None = None
    set_code: str | None = None
    collector_number: str | None = None
    condition: str | None = None
    variant: str | None = None
    language: str | None = None
    foil: bool = False
    promo: bool = False
    origin: str | None = None
    image_path: str | None = None
    quantity: int
    available: int
    unit_cost_eur_cents: int | None = None
    note: str | None = None
    order_id: str | None = None
    seller: str | None = None
    purchase_date: str | None = None


class InventoryLotIn(BaseModel):
    game: str | None = None
    set_code: str | None = None
    collector_number: str | None = None
    name_zh: str | None = None
    name_en: str | None = None
    language: str | None = None
    variant: str | None = None
    foil: bool = False
    promo: bool = False
    condition: str | None = None
    quantity: int = 1
    amount: int = 0
    currency: Currency = Currency.EUR
    note: str | None = None
    image_path: str | None = None


class InventoryLotDetailOut(InventoryLotOut):
    movements: list[MovementOut]


class MovementIn(BaseModel):
    kind: MovementKind
    quantity: int


class SplitIn(BaseModel):
    quantity: int


class ListingIn(BaseModel):
    lot_id: str
    quantity: int
    unit_price_eur_cents: int


class SaleIn(BaseModel):
    quantity: int
    unit_price_eur_cents: int
    fees_eur_cents: int = 0


class ListingOut(BaseModel):
    id: str
    lot_id: str
    quantity: int
    unit_price_eur_cents: int
    status: ListingStatus
    created_at: datetime
    name: str
    name_en: str | None = None
    set_code: str | None = None
    collector_number: str | None = None
    image_path: str | None = None
    available: int


class SaleOut(BaseModel):
    id: str
    lot_id: str
    quantity: int
    unit_price_eur_cents: int
    fees_eur_cents: int
    landed_unit_eur_cents: int
    sold_at: datetime
    name: str
    name_en: str | None = None
    set_code: str | None = None
    collector_number: str | None = None
    revenue_eur_cents: int
    cost_eur_cents: int
    profit_eur_cents: int
    roi_pct: float


class OverviewOut(BaseModel):
    orders_count: int
    invested_eur_cents: int
    inventory_units: int
    inventory_value_eur_cents: int
    sold_units: int
    revenue_eur_cents: int
    cost_eur_cents: int
    profit_eur_cents: int
    roi_pct: float


class CardOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    game: str | None
    set_code: str | None
    collector_number: str | None
    name_zh: str | None
    name_en: str | None
    language: str | None
    variant: str | None
    foil: bool
    promo: bool
    image_path: str | None
    stock_qty: int
    total_qty: int
    avg_price_eur_cents: int | None


class CardPurchaseOut(BaseModel):
    id: str
    order_id: str
    seller: str | None
    purchase_date: str | None
    quantity: int
    unit_price_fen: int
    fx_cny_eur: float
    condition: str | None
    image_path: str | None


class CardLotOut(BaseModel):
    id: str
    quantity: int
    available: int
    unit_cost_eur_cents: int | None
    condition: str | None
    image_path: str | None


class CardDetailOut(CardOut):
    purchases: list[CardPurchaseOut]
    lots: list[CardLotOut]


class CardNameIn(BaseModel):
    name_en: str | None = None


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
    fx_source: str = "fixed"
    items: list[OrderItemIn] = []
    raw_dumps: list[str] = []
    warnings: list[str] = []
    error: str | None = None
