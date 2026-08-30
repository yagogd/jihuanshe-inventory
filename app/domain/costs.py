"""Pure cost engine: largest-remainder allocation and landed cost.

The allocation never stores a single ``landed=44.08`` number; it derives every
line's landed cost from persisted inputs (pools, item values, FX and methods),
so the result is always reproducible and can be recalculated after edits.

Money is integer fen (CNY) / cents (EUR). FX is the frozen per-order rate.
"""
from __future__ import annotations

import math
from collections.abc import Iterable

from app.domain.enums import AllocationMethod, ShipmentCostType
from app.domain.models import Order, OrderItem, Shipment

_TYPE_FIELD = {
    ShipmentCostType.INTERNATIONAL: "international_cents",
    ShipmentCostType.INSURANCE: "insurance_cents",
    ShipmentCostType.CUSTOMS: "customs_cents",
    ShipmentCostType.OTHER: "other_cents",
}


def allocate_largest_remainder(weights: list[int], total: int) -> list[int]:
    """Split ``total`` proportionally to ``weights`` using largest remainder.

    Weights are non-negative integers; items with zero weight receive zero.
    The result is a list of integers whose sum equals ``total``.
    """
    if not weights or total <= 0 or sum(weights) == 0:
        return [0] * len(weights)

    total_weight = sum(weights)
    raw = [w * total / total_weight for w in weights]
    floors = [math.floor(value) for value in raw]
    remainder = total - sum(floors)

    order = sorted(range(len(weights)), key=lambda i: raw[i] - floors[i], reverse=True)
    for index in order[:remainder]:
        floors[index] += 1
    return floors


def _order_weights(items: Iterable[OrderItem], method: AllocationMethod) -> list[int]:
    if method == AllocationMethod.BY_QUANTITY:
        return [item.quantity if item.include_in_allocation else 0 for item in items]
    # BY_VALUE (and MANUAL, pending a manual-entry UI) by line purchase value.
    return [
        item.unit_price_fen * item.quantity if item.include_in_allocation else 0
        for item in items
    ]


def _shipment_weights(
    order_items: list[tuple[Order, OrderItem]], method: AllocationMethod
) -> list[int]:
    if method == AllocationMethod.BY_QUANTITY:
        return [item.quantity if item.include_in_allocation else 0 for _, item in order_items]
    return [
        round(item.unit_price_fen * item.quantity * order.fx_cny_eur)
        if item.include_in_allocation
        else 0
        for order, item in order_items
    ]


def compute_order_landed(order: Order, shipment: Shipment | None = None) -> dict:
    """Return the landed-cost breakdown for every line of ``order``.

    ``shipment``, when present, must be loaded with ``.costs`` and
    ``.orders[].items``. Shipment-level EUR costs are allocated across all
    lines of the shipment; order-level CNY costs are allocated across this
    order's lines only.
    """
    items = list(order.items)

    cny_weights = _order_weights(items, order.cost_method)
    domestic_alloc = allocate_largest_remainder(cny_weights, order.domestic_shipping_fen)
    alipay_alloc = allocate_largest_remainder(cny_weights, order.alipay_fee_fen or 0)

    shipment_alloc: dict[ShipmentCostType, list[int]] = {}
    index_by_item: dict[int, int] = {}
    if shipment is not None:
        order_items = [(o, item) for o in shipment.orders for item in o.items]
        index_by_item = {id(item): index for index, (_, item) in enumerate(order_items)}
        for cost in shipment.costs:
            weights = _shipment_weights(order_items, cost.method)
            shipment_alloc[cost.type] = allocate_largest_remainder(weights, cost.amount_eur_cents)

    result_items = []
    total_landed = 0
    for position, item in enumerate(items):
        purchase = item.unit_price_fen * item.quantity
        domestic = domestic_alloc[position]
        alipay = alipay_alloc[position]
        cny_total = purchase + domestic + alipay
        cny_eur = round(cny_total * order.fx_cny_eur)

        parts = {field: 0 for field in _TYPE_FIELD.values()}
        index = index_by_item.get(id(item))
        for cost_type, allocs in shipment_alloc.items():
            parts[_TYPE_FIELD[cost_type]] = allocs[index] if index is not None else 0
        eur = sum(parts.values())
        landed = cny_eur + eur
        total_landed += landed

        result_items.append(
            {
                "item_id": item.id,
                "name": item.normalized_name or item.raw_name,
                "quantity": item.quantity,
                "purchase_cny_fen": purchase,
                "domestic_cny_fen": domestic,
                "alipay_cny_fen": alipay,
                "cny_total_fen": cny_total,
                "cny_eur_cents": cny_eur,
                "international_cents": parts["international_cents"],
                "insurance_cents": parts["insurance_cents"],
                "customs_cents": parts["customs_cents"],
                "other_cents": parts["other_cents"],
                "landed_eur_cents": landed,
            }
        )

    return {
        "order_id": order.id,
        "fx_cny_eur": order.fx_cny_eur,
        "items": result_items,
        "total_landed_eur_cents": total_landed,
    }
