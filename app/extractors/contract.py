"""Extractor contract (anti-corruption layer).

The rest of the application only ever sees these plain dataclasses. Whether
they were produced by UIAutomator, a network interceptor, or a fixture does not
matter to the domain.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol


@dataclass
class ParsedItem:
    raw_name: str
    quantity: int = 1
    unit_price_fen: int = 0
    set_code: str | None = None
    collector_number: str | None = None
    variant: str | None = None
    promo: bool = False
    foil: bool = False
    game: str | None = None
    language: str | None = None
    condition: str | None = None
    image_bounds: tuple[int, int, int, int] | None = None
    image_path: str | None = None
    position: int = 0


@dataclass
class ParsedOrder:
    screen_title: str | None = None
    has_product_info: bool = False
    declared_item_count: int | None = None
    seller: str | None = None
    jihuanshe_order_id: str | None = None
    purchase_date: str | None = None
    domestic_shipping_fen: int | None = None
    subtotal_fen: int | None = None
    total_paid_fen: int | None = None
    express_company: str | None = None
    express_tracking: str | None = None
    reached_footer: bool = False
    screen_size: tuple[int, int] | None = None
    occlusions: list[tuple[int, int, int, int]] = field(default_factory=list)
    items: list[ParsedItem] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


@dataclass
class CaptureStatus:
    detected: bool
    available: bool = False
    screen_title: str | None = None
    declared_item_count: int | None = None
    error: str | None = None


@dataclass
class CapturePreview:
    detected: bool
    session_id: str | None = None
    screen_title: str | None = None
    declared_item_count: int | None = None
    order: ParsedOrder | None = None
    raw_dumps: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    error: str | None = None


@dataclass
class ListedOrder:
    jihuanshe_order_id: str
    state: str
    seller: str | None
    bounds: tuple[int, int, int, int]

    @property
    def cancelled(self) -> bool:
        return "取消" in self.state or "关闭" in self.state


class OrderExtractor(Protocol):
    def status(self) -> CaptureStatus: ...

    def preview(self) -> CapturePreview: ...
