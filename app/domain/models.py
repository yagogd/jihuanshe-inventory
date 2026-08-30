"""SQLAlchemy ORM models.

Money is stored as integer fen (CNY) / cents (EUR) to avoid floating point
rounding. FX is a rate (float, manually entered). Raw scraper capture is kept
verbatim in ``raw_capture_json`` plus the dumps themselves under ``data/dumps``.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base
from app.domain.enums import (
    AllocationMethod,
    ItemOrigin,
    OrderStatus,
    ShipmentCostType,
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


class OrderItem(Base):
    __tablename__ = "order_items"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    order_id: Mapped[str] = mapped_column(String(36), ForeignKey("orders.id"), index=True)

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


class Shipment(Base):
    __tablename__ = "shipments"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    status: Mapped[ShipmentStatus] = mapped_column(
        SAEnum(ShipmentStatus, native_enum=False), default=ShipmentStatus.PREPARING
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, onupdate=_utcnow
    )

    costs: Mapped[list["ShipmentCost"]] = relationship(
        back_populates="shipment", cascade="all, delete-orphan"
    )
    orders: Mapped[list["Order"]] = relationship(back_populates="shipment")


class ShipmentCost(Base):
    __tablename__ = "shipment_costs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    shipment_id: Mapped[str] = mapped_column(String(36), ForeignKey("shipments.id"), index=True)

    type: Mapped[ShipmentCostType] = mapped_column(
        SAEnum(ShipmentCostType, native_enum=False)
    )
    amount_eur_cents: Mapped[int] = mapped_column(Integer, default=0)
    method: Mapped[AllocationMethod] = mapped_column(
        SAEnum(AllocationMethod, native_enum=False), default=AllocationMethod.BY_VALUE
    )

    shipment: Mapped["Shipment"] = relationship(back_populates="costs")
