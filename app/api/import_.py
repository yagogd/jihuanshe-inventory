"""Import endpoints: detect and automatically capture the current order."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db import get_db
from app.deps import get_extractor
from app.domain.fx import resolve_cny_eur
from app.domain.orders import suggest_alipay_fee
from app.domain.schemas import ImportPreviewOut, ImportStatusOut, OrderItemIn
from app.domain.settings import get_app_settings
from app.extractors.contract import CapturePreview

router = APIRouter(prefix="/import", tags=["import"])


def _build_preview(preview: CapturePreview, db: Session) -> ImportPreviewOut:
    if not preview.detected or preview.order is None:
        return ImportPreviewOut(detected=False, error="No se detectó una pantalla de orden")

    app_settings = get_app_settings(db)
    order = preview.order
    subtotal = sum(item.unit_price_fen * item.quantity for item in order.items)
    suggested = suggest_alipay_fee(
        subtotal,
        order.domestic_shipping_fen,
        app_settings.alipay_fee_threshold_fen,
        app_settings.alipay_fee_rate,
    )
    fx, fx_source = resolve_cny_eur(db, order.purchase_date)

    items = [
        OrderItemIn(
            raw_name=item.raw_name,
            normalized_name=item.raw_name,
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
            image_path=item.image_path,
            position=item.position,
        )
        for item in order.items
    ]

    return ImportPreviewOut(
        detected=True,
        session_id=preview.session_id,
        screen_title=preview.screen_title,
        declared_item_count=preview.declared_item_count,
        jihuanshe_order_id=order.jihuanshe_order_id,
        seller=order.seller,
        purchase_date=order.purchase_date,
        express_company=order.express_company,
        express_tracking=order.express_tracking,
        subtotal_fen=subtotal,
        declared_subtotal_fen=order.subtotal_fen,
        domestic_shipping_fen=order.domestic_shipping_fen,
        declared_total_paid_fen=order.total_paid_fen,
        suggested_alipay_fee_fen=suggested,
        fx_cny_eur=fx,
        fx_source=fx_source,
        items=items,
        raw_dumps=preview.raw_dumps,
        warnings=preview.warnings,
    )


@router.get("/status", response_model=ImportStatusOut)
def import_status(extractor=Depends(get_extractor)) -> ImportStatusOut:
    status = extractor.status()
    return ImportStatusOut(
        available=status.available,
        detected=status.detected,
        screen_title=status.screen_title,
        declared_item_count=status.declared_item_count,
        error=status.error,
    )


@router.post("/preview", response_model=ImportPreviewOut)
def import_preview(
    extractor=Depends(get_extractor),
    db: Session = Depends(get_db),
) -> ImportPreviewOut:
    preview = extractor.preview(auto_scroll=True)
    if preview.error:
        raise HTTPException(status_code=422, detail=preview.error)
    return _build_preview(preview, db)
