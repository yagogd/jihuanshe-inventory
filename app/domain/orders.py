"""Order domain services: money math and persistence.

Kept free of FastAPI and extractor dependencies so it can be unit-tested in
isolation. The Alipay fee rule lives here (a later phase will make the
threshold/rate user-configurable; for now they come from settings).
"""
from __future__ import annotations

import json

from sqlalchemy.orm import Session

from app.config import Settings
from app.domain.enums import OrderStatus
from app.domain.models import Order, OrderItem
from app.domain.schemas import OrderIn
from app.extractors.uiautomator.images import relocate_images


def suggest_alipay_fee(subtotal_fen: int, domestic_fen: int | None, settings: Settings) -> int:
    base = subtotal_fen + (domestic_fen or 0)
    if base > settings.alipay_fee_threshold_fen:
        return int(round(base * settings.alipay_fee_rate))
    return 0


def persist_order(db: Session, payload: OrderIn, settings: Settings) -> Order:
    subtotal = sum(item.unit_price_fen * item.quantity for item in payload.items)
    domestic = payload.domestic_shipping_fen or 0
    alipay = (
        payload.alipay_fee_fen
        if payload.alipay_fee_fen is not None
        else suggest_alipay_fee(subtotal, domestic, settings)
    )
    total = (
        payload.total_paid_fen
        if payload.total_paid_fen is not None
        else subtotal + domestic + alipay
    )
    fx = payload.fx_cny_eur if payload.fx_cny_eur is not None else settings.fx_cny_eur

    order = Order(
        jihuanshe_order_id=payload.jihuanshe_order_id,
        seller=payload.seller,
        purchase_date=payload.purchase_date,
        express_company=payload.express_company,
        express_tracking=payload.express_tracking,
        subtotal_fen=subtotal,
        domestic_shipping_fen=domestic,
        alipay_fee_fen=alipay,
        total_paid_fen=total,
        fx_cny_eur=fx,
        fx_source=payload.fx_source or "manual",
        status=OrderStatus.PURCHASED,
    )

    for position, item in enumerate(payload.items):
        order.items.append(
            OrderItem(
                external_card_id=item.external_card_id,
                raw_name=item.raw_name,
                normalized_name=item.normalized_name or item.raw_name,
                game=item.game,
                set_code=item.set_code,
                collector_number=item.collector_number,
                language=item.language,
                condition=item.condition,
                variant=item.variant,
                promo=item.promo,
                foil=item.foil,
                quantity=item.quantity,
                unit_price_fen=item.unit_price_fen,
                origin=item.origin,
                include_in_allocation=item.include_in_allocation,
                image_path=item.image_path,
                position=position,
            )
        )

    db.add(order)
    db.flush()

    if payload.raw_dumps:
        dump_dir = settings.dumps_dir / order.id
        dump_dir.mkdir(parents=True, exist_ok=True)
        rel_paths = []
        for index, xml_text in enumerate(payload.raw_dumps):
            path = dump_dir / f"dump_{index:02d}.xml"
            path.write_text(xml_text, encoding="utf-8")
            rel_paths.append(f"data/dumps/{order.id}/dump_{index:02d}.xml")
        order.raw_capture_json = json.dumps(
            {
                "source": "uiautomator",
                "dumps": rel_paths,
                "warnings": payload.warnings,
                "declared_item_count": payload.declared_item_count,
            },
            ensure_ascii=False,
        )

    if payload.session_id:
        relocate_images(settings.images_dir, order.id, order.items)

    db.commit()
    db.refresh(order)
    return order


def update_order(db: Session, order: Order, payload: OrderIn, settings: Settings) -> Order:
    """Replace editable order data and recalculate all purchase totals."""
    subtotal = sum(item.unit_price_fen * item.quantity for item in payload.items)
    domestic = payload.domestic_shipping_fen or 0
    alipay = (
        payload.alipay_fee_fen
        if payload.alipay_fee_fen is not None
        else suggest_alipay_fee(subtotal, domestic, settings)
    )

    order.jihuanshe_order_id = payload.jihuanshe_order_id
    order.seller = payload.seller
    order.purchase_date = payload.purchase_date
    order.express_company = payload.express_company
    order.express_tracking = payload.express_tracking
    order.subtotal_fen = subtotal
    order.domestic_shipping_fen = domestic
    order.alipay_fee_fen = alipay
    order.total_paid_fen = (
        payload.total_paid_fen
        if payload.total_paid_fen is not None
        else subtotal + domestic + alipay
    )
    order.fx_cny_eur = payload.fx_cny_eur if payload.fx_cny_eur is not None else settings.fx_cny_eur
    order.fx_source = payload.fx_source or order.fx_source or "manual"

    order.items.clear()
    for position, item in enumerate(payload.items):
        order.items.append(
            OrderItem(
                external_card_id=item.external_card_id,
                raw_name=item.raw_name,
                normalized_name=item.normalized_name or item.raw_name,
                game=item.game,
                set_code=item.set_code,
                collector_number=item.collector_number,
                language=item.language,
                condition=item.condition,
                variant=item.variant,
                promo=item.promo,
                foil=item.foil,
                quantity=item.quantity,
                unit_price_fen=item.unit_price_fen,
                origin=item.origin,
                include_in_allocation=item.include_in_allocation,
                image_path=item.image_path,
                position=position,
            )
        )

    db.commit()
    db.refresh(order)
    return order
