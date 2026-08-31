"""SQLAlchemy ORM models.

Money is stored as integer fen (CNY) / cents (EUR) to avoid floating point
rounding. FX is a rate (float, manually entered). Raw scraper capture is kept
verbatim in ``raw_capture_json`` plus the dumps themselves under ``data/dumps``.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    select,
)
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, object_session, relationship

from app.db import Base
from app.domain.enums import (
    AllocationMethod,
    CostCategoryKind,
    Currency,
    ItemOrigin,
    ListingStatus,
    MovementKind,
    OrderStatus,
    ShipmentStatus,
)


def _uuid() -> str:
    return str(uuid.uuid4())


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class AppSettings(Base):
    """Single-row table of user-editable business settings.

    Environment variables provide the initial seed values; afterwards the row
    is authoritative and can be edited through the UI without touching env.
    """

    __tablename__ = "settings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    alipay_fee_threshold_fen: Mapped[int] = mapped_column(Integer, default=20000)
    alipay_fee_rate: Mapped[float] = mapped_column(Float, default=0.03)
    fx_cny_eur: Mapped[float] = mapped_column(Float, default=0.13)
    fx_mode: Mapped[str] = mapped_column(String, default="historical")


class FxRate(Base):
    """Cached EUR exchange rate for a single date, so we never re-fetch it."""

    __tablename__ = "fx_rates"
    __table_args__ = (UniqueConstraint("date", "quote", name="uq_fx_rate"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    date: Mapped[str] = mapped_column(String)
    quote: Mapped[str] = mapped_column(String)
    rate: Mapped[float] = mapped_column(Float)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)


class Card(Base):
    """Catalog identity of a card, unique by ``(game, set_code, collector_number)``.

    The Chinese name is the scraped source of truth; ``name_en`` is a best-effort
    translation cached here so it is only ever looked up once. Price, quantity
    and condition never live here: those belong to purchases and lots.
    """

    __tablename__ = "cards"
    __table_args__ = (
        UniqueConstraint("game", "set_code", "collector_number", name="uq_card_identity"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    game: Mapped[str | None] = mapped_column(String, nullable=True)
    set_code: Mapped[str | None] = mapped_column(String, nullable=True)
    collector_number: Mapped[str | None] = mapped_column(String, nullable=True)

    name_zh: Mapped[str | None] = mapped_column(String, nullable=True)
    name_en: Mapped[str | None] = mapped_column(String, nullable=True)

    language: Mapped[str | None] = mapped_column(String, nullable=True)
    variant: Mapped[str | None] = mapped_column(String, nullable=True)
    foil: Mapped[bool] = mapped_column(Boolean, default=False)
    promo: Mapped[bool] = mapped_column(Boolean, default=False)

    image_path: Mapped[str | None] = mapped_column(String, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, onupdate=_utcnow
    )

    items: Mapped[list["OrderItem"]] = relationship(back_populates="card")


class Order(Base):
    __tablename__ = "orders"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    jihuanshe_order_id: Mapped[str | None] = mapped_column(String, nullable=True, unique=True)
    seller: Mapped[str | None] = mapped_column(String, nullable=True)
    purchase_date: Mapped[str | None] = mapped_column(String, nullable=True)
    express_company: Mapped[str | None] = mapped_column(String, nullable=True)
    express_tracking: Mapped[str | None] = mapped_column(String, nullable=True)

    subtotal_fen: Mapped[int] = mapped_column(Integer, default=0)
    domestic_shipping_fen: Mapped[int] = mapped_column(Integer, default=0)
    alipay_fee_fen: Mapped[int | None] = mapped_column(Integer, nullable=True)
    total_paid_fen: Mapped[int] = mapped_column(Integer, default=0)

    fx_cny_eur: Mapped[float] = mapped_column(Float, default=0.13)
    fx_source: Mapped[str] = mapped_column(String, default="manual")
    card_charged_eur_cents: Mapped[int | None] = mapped_column(Integer, nullable=True)
    cost_method: Mapped[AllocationMethod] = mapped_column(
        SAEnum(AllocationMethod, native_enum=False), default=AllocationMethod.BY_VALUE
    )

    status: Mapped[OrderStatus] = mapped_column(
        SAEnum(OrderStatus, native_enum=False), default=OrderStatus.PURCHASED
    )
    raw_capture_json: Mapped[str | None] = mapped_column(Text, nullable=True)

    shipment_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("shipments.id"), nullable=True, index=True
    )
    shipment: Mapped["Shipment | None"] = relationship(back_populates="orders")

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, onupdate=_utcnow
    )

    items: Mapped[list["OrderItem"]] = relationship(
        back_populates="order", cascade="all, delete-orphan", order_by="OrderItem.position"
    )

    @property
    def has_sales(self) -> bool:
        session = object_session(self)
        if session is None:
            return False
        return (
            session.scalar(
                select(Sale.id)
                .join(InventoryLot, Sale.lot_id == InventoryLot.id)
                .join(OrderItem, InventoryLot.order_item_id == OrderItem.id)
                .where(OrderItem.order_id == self.id)
                .limit(1)
            )
            is not None
        )


class OrderItem(Base):
    __tablename__ = "order_items"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    order_id: Mapped[str] = mapped_column(String(36), ForeignKey("orders.id"), index=True)
    card_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("cards.id"), nullable=True, index=True
    )

    external_card_id: Mapped[str | None] = mapped_column(String, nullable=True)
    raw_name: Mapped[str] = mapped_column(String)
    normalized_name: Mapped[str] = mapped_column(String)

    game: Mapped[str | None] = mapped_column(String, nullable=True)
    set_code: Mapped[str | None] = mapped_column(String, nullable=True)
    collector_number: Mapped[str | None] = mapped_column(String, nullable=True)
    language: Mapped[str | None] = mapped_column(String, nullable=True)
    condition: Mapped[str | None] = mapped_column(String, nullable=True)
    variant: Mapped[str | None] = mapped_column(String, nullable=True)
    promo: Mapped[bool] = mapped_column(Boolean, default=False)
    foil: Mapped[bool] = mapped_column(Boolean, default=False)

    quantity: Mapped[int] = mapped_column(Integer, default=1)
    unit_price_fen: Mapped[int] = mapped_column(Integer, default=0)

    origin: Mapped[ItemOrigin] = mapped_column(
        SAEnum(ItemOrigin, native_enum=False), default=ItemOrigin.SCRAPED
    )
    include_in_allocation: Mapped[bool] = mapped_column(Boolean, default=True)
    image_path: Mapped[str | None] = mapped_column(String, nullable=True)
    position: Mapped[int] = mapped_column(Integer, default=0)

    order: Mapped["Order"] = relationship(back_populates="items")
    card: Mapped["Card | None"] = relationship(back_populates="items")
    lots: Mapped[list["InventoryLot"]] = relationship(
        back_populates="order_item", cascade="all, delete-orphan"
    )


class Shipment(Base):
    __tablename__ = "shipments"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    status: Mapped[ShipmentStatus] = mapped_column(
        SAEnum(ShipmentStatus, native_enum=False), default=ShipmentStatus.PREPARING
    )
    total_paid_eur_cents: Mapped[int] = mapped_column(Integer, default=0)
    fx_cny_eur: Mapped[float] = mapped_column(Float, default=0.13)
    fx_source: Mapped[str] = mapped_column(String, default="fixed")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, onupdate=_utcnow
    )

    costs: Mapped[list["ShipmentCost"]] = relationship(
        back_populates="shipment", cascade="all, delete-orphan", order_by="ShipmentCost.position"
    )
    orders: Mapped[list["Order"]] = relationship(back_populates="shipment")

    @property
    def has_sales(self) -> bool:
        session = object_session(self)
        if session is None:
            return False
        return (
            session.scalar(
                select(Sale.id)
                .join(InventoryLot, Sale.lot_id == InventoryLot.id)
                .join(OrderItem, InventoryLot.order_item_id == OrderItem.id)
                .join(Order, OrderItem.order_id == Order.id)
                .where(Order.shipment_id == self.id)
                .limit(1)
            )
            is not None
        )


class CostCategory(Base):
    """A reusable shipping-cost bucket. The user can add their own."""

    __tablename__ = "cost_categories"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    name: Mapped[str] = mapped_column(String, unique=True)
    kind: Mapped[CostCategoryKind] = mapped_column(
        SAEnum(CostCategoryKind, native_enum=False), default=CostCategoryKind.CUSTOM
    )
    position: Mapped[int] = mapped_column(Integer, default=0)


class ShipmentCost(Base):
    __tablename__ = "shipment_costs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    shipment_id: Mapped[str] = mapped_column(String(36), ForeignKey("shipments.id"), index=True)
    category_id: Mapped[str] = mapped_column(String(36), ForeignKey("cost_categories.id"))

    amount: Mapped[int] = mapped_column(Integer, default=0)
    currency: Mapped[Currency] = mapped_column(
        SAEnum(Currency, native_enum=False), default=Currency.EUR
    )
    method: Mapped[AllocationMethod] = mapped_column(
        SAEnum(AllocationMethod, native_enum=False), default=AllocationMethod.BY_VALUE
    )
    insured_amount: Mapped[int | None] = mapped_column(Integer, nullable=True)
    insured_currency: Mapped[Currency | None] = mapped_column(
        SAEnum(Currency, native_enum=False), nullable=True
    )
    position: Mapped[int] = mapped_column(Integer, default=0)

    shipment: Mapped["Shipment"] = relationship(back_populates="costs")
    category: Mapped["CostCategory"] = relationship()


class InventoryLot(Base):
    __tablename__ = "inventory_lots"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    order_item_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("order_items.id"), index=True
    )
    quantity: Mapped[int] = mapped_column(Integer, default=0)
    available: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    order_item: Mapped["OrderItem"] = relationship(back_populates="lots")
    movements: Mapped[list["LotMovement"]] = relationship(
        back_populates="lot", cascade="all, delete-orphan", order_by="LotMovement.created_at"
    )
    listings: Mapped[list["Listing"]] = relationship(
        back_populates="lot", cascade="all, delete-orphan"
    )


class LotMovement(Base):
    __tablename__ = "lot_movements"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    lot_id: Mapped[str] = mapped_column(String(36), ForeignKey("inventory_lots.id"), index=True)
    kind: Mapped[MovementKind] = mapped_column(SAEnum(MovementKind, native_enum=False))
    delta: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    lot: Mapped["InventoryLot"] = relationship(back_populates="movements")


class Listing(Base):
    __tablename__ = "listings"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    lot_id: Mapped[str] = mapped_column(String(36), ForeignKey("inventory_lots.id"), index=True)
    quantity: Mapped[int] = mapped_column(Integer, default=1)
    unit_price_eur_cents: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[ListingStatus] = mapped_column(
        SAEnum(ListingStatus, native_enum=False), default=ListingStatus.ACTIVE
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    lot: Mapped["InventoryLot"] = relationship(back_populates="listings")


class Sale(Base):
    __tablename__ = "sales"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    lot_id: Mapped[str] = mapped_column(String(36), ForeignKey("inventory_lots.id"), index=True)
    quantity: Mapped[int] = mapped_column(Integer, default=1)
    unit_price_eur_cents: Mapped[int] = mapped_column(Integer, default=0)
    fees_eur_cents: Mapped[int] = mapped_column(Integer, default=0)
    landed_unit_eur_cents: Mapped[int] = mapped_column(Integer, default=0)
    landed_snapshot_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    sold_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    lot: Mapped["InventoryLot"] = relationship()
