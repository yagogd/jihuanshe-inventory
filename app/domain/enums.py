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


class ShipmentStatus(str, Enum):
    PREPARING = "PREPARING"
    SHIPPED = "SHIPPED"
    RECEIVED = "RECEIVED"


class ShipmentCostType(str, Enum):
    INTERNATIONAL = "INTERNATIONAL"
    INSURANCE = "INSURANCE"
    CUSTOMS = "CUSTOMS"
    OTHER = "OTHER"


class AllocationMethod(str, Enum):
    BY_VALUE = "BY_VALUE"
    BY_QUANTITY = "BY_QUANTITY"
    MANUAL = "MANUAL"


class MovementKind(str, Enum):
    RECEIVE = "RECEIVE"
    SELL = "SELL"
    GRADE = "GRADE"
    SPLIT_OUT = "SPLIT_OUT"
    SPLIT_IN = "SPLIT_IN"
