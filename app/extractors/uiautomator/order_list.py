"""Parse the purchased-orders list without depending on translated labels."""
from __future__ import annotations

import re
import xml.etree.ElementTree as ET

from app.extractors.contract import ListedOrder

_BOUNDS_RE = re.compile(r"\[(\d+),(\d+)\]\[(\d+),(\d+)\]")


def _bounds(value: str) -> tuple[int, int, int, int] | None:
    match = _BOUNDS_RE.fullmatch(value)
    return tuple(map(int, match.groups())) if match else None


def parse_order_list(xml: str) -> list[ListedOrder]:
    """Return complete visible order cards (partial cards are ignored)."""
    try:
        root = ET.fromstring(xml)
    except ET.ParseError:
        return []

    result: list[ListedOrder] = []
    for card in root.iter():
        if card.attrib.get("clickable") != "true":
            continue
        descendants = list(card.iter())
        number_node = next(
            (node for node in descendants if node.attrib.get("resource-id", "").endswith("/orderNumTv")),
            None,
        )
        state_node = next(
            (node for node in descendants if node.attrib.get("resource-id", "").endswith("/stateTv")),
            None,
        )
        bounds = _bounds(card.attrib.get("bounds", ""))
        if number_node is None or state_node is None or bounds is None:
            continue
        order_id = number_node.attrib.get("text", "").strip()
        state = state_node.attrib.get("text", "").strip()
        if not order_id or not state:
            continue
        seller_group = next(
            (node for node in descendants if node.attrib.get("resource-id", "").endswith("/userNameTv")),
            None,
        )
        seller = None
        if seller_group is not None:
            seller = next(
                (node.attrib.get("text") for node in seller_group.iter() if node.attrib.get("text")),
                None,
            )
        result.append(ListedOrder(order_id, state, seller, bounds))
    return result
