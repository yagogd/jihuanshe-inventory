"""Parse a UIAutomator window XML into a ParsedOrder.

Only the product list (``contentView`` nodes) is understood; each card is one
``contentView``. A node is considered complete only when it exposes a name, a
price and a quantity (``tv_num``). Truncated nodes (the last visible card cut
off at the bottom of the screen) are discarded.
"""
from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from decimal import Decimal, InvalidOperation

from app.extractors.contract import ParsedItem, ParsedOrder

ORDER_DETAIL_TITLE = "订单详情"
PRODUCT_INFO_TITLE = "商品信息"

_NUMBERING_RE = re.compile(r"^([A-Za-z0-9]+)\s*[·:：-]\s*(.+)$")
_QTY_RE = re.compile(r"(\d+)")
_BOUNDS_RE = re.compile(r"\[(\d+),(\d+)\]\[(\d+),(\d+)\]")
_YUAN_RE = re.compile(r"([\d,.]+)\s*元$")

FOOTER_LABEL = "实付款"


def _rid(node: ET.Element) -> str:
    rid = node.attrib.get("resource-id", "")
    return rid.split("/")[-1] if rid else ""


def parse_window_xml(xml_text: str) -> ParsedOrder:
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError as exc:
        return ParsedOrder(warnings=[f"XML inválido: {exc}"])

    nodes = list(root.iter("node"))

    screen_title: str | None = None
    has_product_info = False
    declared: int | None = None
    for node in nodes:
        text = node.attrib.get("text", "")
        if text == ORDER_DETAIL_TITLE:
            screen_title = text
        if text == PRODUCT_INFO_TITLE:
            has_product_info = True
        if _rid(node) == "tvNum":
            has_product_info = True
            declared = _parse_int(node.attrib.get("text", ""))

    seller = _label_value(nodes, "sellerNameTv")
    jihuanshe_order_id = _label_value(nodes, "orderNumTv")
    purchase_date = _label_value(nodes, "orderTimeTv")
    express_company, express_tracking = _express_info(nodes)
    domestic_shipping = _container_price(nodes, "llShipping")
    subtotal = _container_price(nodes, "llProductsPrice")
    total_paid = _total_paid(nodes)
    reached_footer = _text_seen(nodes, FOOTER_LABEL) or any(
        _rid(n) in ("llShipping", "llProductsPrice") for n in nodes
    )
    screen_size = _screen_size(nodes)
    occlusions = _occlusions(nodes)

    items: list[ParsedItem] = []
    warnings: list[str] = []
    for position, node in enumerate(nodes):
        if _rid(node) != "contentView":
            continue
        item = _parse_content_view(node, position)
        if item is None:
            warnings.append(f"ítem incompleto en posición {position} (ignorado)")
        else:
            items.append(item)

    order = ParsedOrder(
        screen_title=screen_title,
        has_product_info=has_product_info,
        declared_item_count=declared,
        seller=seller,
        jihuanshe_order_id=jihuanshe_order_id,
        purchase_date=purchase_date,
        domestic_shipping_fen=domestic_shipping,
        subtotal_fen=subtotal,
        total_paid_fen=total_paid,
        express_company=express_company,
        express_tracking=express_tracking,
        reached_footer=reached_footer,
        screen_size=screen_size,
        occlusions=occlusions,
        items=items,
        warnings=warnings,
    )
    return order


def _parse_content_view(cv: ET.Element, position: int) -> ParsedItem | None:
    name = _child_text(cv, "officialNameTv")
    price_raw = _child_text(cv, "priceView")
    qty_raw = _child_text(cv, "tv_num")
    if not name or not price_raw or not qty_raw:
        return None

    price = _parse_price(price_raw)
    qty = _parse_qty(qty_raw)
    if price is None or qty is None:
        return None

    numbering = _child_text(cv, "tv_numbering")
    set_code, collector_number = _parse_numbering(numbering)
    variant = _child_text(cv, "tv_preciousness")

    return ParsedItem(
        raw_name=name.strip(),
        quantity=qty,
        unit_price_fen=price,
        set_code=set_code,
        collector_number=collector_number,
        variant=variant,
        promo=(variant or "").strip().lower() == "promo",
        game=_child_text(cv, "gameNameTv"),
        language=_child_text(cv, "tvLan"),
        condition=_child_text_deep(cv, "rateIdView"),
        image_bounds=_parse_bounds(_image_bounds(cv)),
        position=position,
    )


def _child_text(cv: ET.Element, rid_name: str) -> str | None:
    for node in cv.iter("node"):
        if _rid(node) == rid_name:
            return node.attrib.get("text", "").strip() or None
    return None


def _label_value(nodes: list[ET.Element], label_rid: str) -> str | None:
    """Value of a header field: the next plain text node after its label.

    Jihuanshe renders the label with a resource-id (e.g. ``sellerNameTv``) and
    the actual value in a following node that has no resource-id.
    """
    for index, node in enumerate(nodes):
        if _rid(node) != label_rid:
            continue
        for candidate in nodes[index + 1 :]:
            if _rid(candidate):
                return None
            text = candidate.attrib.get("text", "").strip()
            if text:
                return text
        return None
    return None


def _express_info(nodes: list[ET.Element]) -> tuple[str | None, str | None]:
    """First two text nodes inside ``expressContent``: company then tracking id."""
    for node in nodes:
        if _rid(node) != "expressContent":
            continue
        texts = [
            descendant.attrib.get("text", "").strip()
            for descendant in node.iter("node")
            if descendant.attrib.get("text", "").strip()
        ]
        return (texts[0] if len(texts) > 0 else None), (texts[1] if len(texts) > 1 else None)
    return None, None


def _container_price(nodes: list[ET.Element], container_rid: str) -> int | None:
    """Money value inside a footer container, formatted like ``18元`` / ``1025元``."""
    for node in nodes:
        if _rid(node) != container_rid:
            continue
        for descendant in node.iter("node"):
            text = descendant.attrib.get("text", "").strip()
            match = _YUAN_RE.match(text)
            if match:
                return _parse_price(match.group(1))
        return None
    return None


def _total_paid(nodes: list[ET.Element]) -> int | None:
    """The ``priceView`` that follows the ``实付款`` label."""
    for index, node in enumerate(nodes):
        if node.attrib.get("text", "").strip() != FOOTER_LABEL:
            continue
        for candidate in nodes[index + 1 :]:
            if _rid(candidate) == "priceView":
                return _parse_price(candidate.attrib.get("text", ""))
    return None


def _text_seen(nodes: list[ET.Element], text: str) -> bool:
    return any(node.attrib.get("text", "").strip() == text for node in nodes)


def _screen_size(nodes: list[ET.Element]) -> tuple[int, int] | None:
    """Screen dimensions from the root node's bounds (e.g. 1272x2800)."""
    if not nodes:
        return None
    bounds = _parse_bounds(nodes[0].attrib.get("bounds", ""))
    if bounds is None:
        return None
    return bounds[2], bounds[3]


def _occlusions(nodes: list[ET.Element]) -> list[tuple[int, int, int, int]]:
    """Bounds of fixed UI that covers card images: the top app bar and the
    bottom 查看评价 button. Cards hidden behind them are skipped when cropping.
    """
    result = []
    for node in nodes:
        text = node.attrib.get("text", "").strip()
        if text == "查看评价" or _rid(node) == "app_bar":
            bounds = _parse_bounds(node.attrib.get("bounds", ""))
            if bounds is not None:
                result.append(bounds)
    return result


def _child_text_deep(cv: ET.Element, rid_name: str) -> str | None:
    for node in cv.iter("node"):
        if _rid(node) == rid_name:
            for descendant in node.iter("node"):
                text = descendant.attrib.get("text", "").strip()
                if text:
                    return text
    return None


def _image_bounds(cv: ET.Element) -> str | None:
    for node in cv.iter("node"):
        if _rid(node) == "image":
            return node.attrib.get("bounds", "")
    return None


def _parse_int(text: str) -> int | None:
    try:
        return int(text.strip())
    except ValueError:
        return None


def _parse_price(text: str) -> int | None:
    try:
        value = Decimal(text.strip().replace(",", ""))
        return int((value * 100).quantize(Decimal("1")))
    except (InvalidOperation, ValueError):
        return None


def _parse_qty(text: str) -> int | None:
    match = _QTY_RE.search(text)
    return int(match.group(1)) if match else None


def _parse_numbering(text: str | None) -> tuple[str | None, str | None]:
    if not text:
        return None, None
    cleaned = text.strip().lstrip("·•. :：")
    match = _NUMBERING_RE.match(cleaned)
    if match:
        return match.group(1), match.group(2)
    return None, cleaned


def _parse_bounds(text: str | None) -> tuple[int, int, int, int] | None:
    if not text:
        return None
    match = _BOUNDS_RE.match(text)
    if not match:
        return None
    return tuple(int(g) for g in match.groups())  # type: ignore[return-value]
