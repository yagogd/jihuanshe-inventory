"""Import endpoints: detect and automatically capture the current order."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.deps import get_extractor
from app.domain.fx import resolve_cny_eur
from app.domain.models import Order
from app.domain.orders import persist_order, suggest_alipay_fee
from app.domain.schemas import (
    BulkImportItemOut,
    BulkImportOut,
    ImportPreviewOut,
    ImportStatusOut,
    OrderIn,
    OrderItemIn,
)
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


def _preview_to_order(preview: ImportPreviewOut) -> OrderIn:
    return OrderIn(
        jihuanshe_order_id=preview.jihuanshe_order_id,
        seller=preview.seller,
        purchase_date=preview.purchase_date,
        express_company=preview.express_company,
        express_tracking=preview.express_tracking,
        domestic_shipping_fen=preview.domestic_shipping_fen,
        total_paid_fen=preview.declared_total_paid_fen,
        items=preview.items,
        session_id=preview.session_id,
        raw_dumps=preview.raw_dumps,
        warnings=preview.warnings,
        declared_item_count=preview.declared_item_count,
    )


@router.post("/bulk", response_model=BulkImportOut)
def bulk_import_orders(
    extractor=Depends(get_extractor),
    db: Session = Depends(get_db),
) -> BulkImportOut:
    """Walk the current purchased-orders list and persist every unseen order."""
    registered = {
        order.jihuanshe_order_id: order.id
        for order in db.scalars(select(Order)).all()
        if order.jihuanshe_order_id
    }
    handled: set[str] = set()
    items: list[BulkImportItemOut] = []
    stuck = 0
    previous_signature = None
    reached_end = False
    scrolls = 0

    while scrolls < extractor.settings.max_scrolls:
        visible = extractor.visible_listed_orders()
        if not visible:
            raise HTTPException(
                status_code=422,
                detail="No se detectó el listado de órdenes compradas en pantalla",
            )

        candidate = next(
            (
                order
                for order in visible
                if order.jihuanshe_order_id not in handled
                and order.jihuanshe_order_id not in registered
                and not order.cancelled
            ),
            None,
        )
        for order in visible:
            order_id = order.jihuanshe_order_id
            if order_id in handled:
                continue
            if order.cancelled:
                handled.add(order_id)
                items.append(BulkImportItemOut(
                    jihuanshe_order_id=order_id, seller=order.seller, status="cancelled"
                ))
            elif order_id in registered:
                handled.add(order_id)
                items.append(BulkImportItemOut(
                    jihuanshe_order_id=order_id,
                    seller=order.seller,
                    status="already_registered",
                    order_id=registered[order_id],
                ))

        if candidate is not None:
            expected_id = candidate.jihuanshe_order_id
            handled.add(expected_id)
            error = None
            created = None
            opened = extractor.open_listed_order(candidate)
            if not opened:
                error = "No se pudo abrir la orden"
            else:
                try:
                    capture = extractor.preview(auto_scroll=True)
                    if capture.error:
                        error = capture.error
                    else:
                        built = _build_preview(capture, db)
                        if not built.detected:
                            error = built.error or "No se detectó la orden abierta"
                        elif built.jihuanshe_order_id != expected_id:
                            error = (
                                f"La orden abierta no coincide: esperada {expected_id}, "
                                f"detectada {built.jihuanshe_order_id or 'sin número'}"
                            )
                        else:
                            created = persist_order(db, _preview_to_order(built))
                            registered[expected_id] = created.id
                except Exception as exc:
                    db.rollback()
                    error = f"Error al guardar: {exc}"
            if opened and not extractor.return_to_order_list():
                raise HTTPException(
                    status_code=422,
                    detail="No se pudo volver al listado después de escanear una orden",
                )
            items.append(BulkImportItemOut(
                jihuanshe_order_id=expected_id,
                seller=candidate.seller,
                status="failed" if error else "imported",
                order_id=created.id if created else None,
                error=error,
            ))
            previous_signature = None
            stuck = 0
            continue

        signature = tuple((order.jihuanshe_order_id, order.bounds) for order in visible)
        if signature == previous_signature:
            stuck += 1
            if stuck >= 2:
                reached_end = True
                break
        else:
            stuck = 0
        previous_signature = signature
        extractor.scroll_order_list()
        scrolls += 1

    return BulkImportOut(
        imported=sum(item.status == "imported" for item in items),
        already_registered=sum(item.status == "already_registered" for item in items),
        cancelled=sum(item.status == "cancelled" for item in items),
        failed=sum(item.status == "failed" for item in items),
        reached_end=reached_end,
        items=items,
    )
