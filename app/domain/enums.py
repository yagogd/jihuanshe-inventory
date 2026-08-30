from __future__ import annotations

from enum import Enum


class OrderStatus(str, Enum):
    PURCHASED = "PURCHASED"
    IN_TRANSIT_TO_WAREHOUSE = "IN_TRANSIT_TO_WAREHOUSE"
    AT_WAREHOUSE = "AT_WAREHOUSE"


class ItemOrigin(str, Enum):
    SCRAPED = "SCRAPED"
    MANUAL = "MANUAL"
    SELLER_GIFT = "SELLER_GIFT"
    BULK = "BULK"
    ADJUSTMENT = "ADJUSTMENT"
