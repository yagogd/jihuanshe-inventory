"""Accumulating capture session.

A session keeps state across many screen captures (either user-driven manual
scrolling or the auto-scroll loop): it merges header fields, deduplicates card
items by sequence overlap, and crops only cleanly-visible card images.
"""
from __future__ import annotations

import time
import uuid
from typing import Any

from app.config import Settings
from app.extractors.contract import CapturePreview, ParsedOrder
from app.extractors.uiautomator.images import crop_if_clean, image_filename
from app.extractors.uiautomator.merge import item_fingerprint, merge_items
from app.extractors.uiautomator.parse import parse_window_xml


class CaptureSession:
    def __init__(self, session_id: str, settings: Settings, images_dir):
        self.session_id = session_id
        self.settings = settings
        self.images_dir = images_dir
        self.rel_dir = f"preview/{session_id}"
        self.created_at = time.monotonic()
        self.header = ParsedOrder()
        self.items = []
        self.dumps: list[str] = []
        self.declared: int | None = None
        self.screen_title: str | None = None
        self.footer: dict[str, Any] = {
            "domestic_shipping_fen": None,
            "subtotal_fen": None,
            "total_paid_fen": None,
            "reached": False,
        }
        self.warnings: list[str] = []

    def ingest(self, xml: str, shot: bytes | None, with_items: bool = True) -> None:
        order = parse_window_xml(xml)
        self.dumps.append(xml)

        self.header.screen_title = self.header.screen_title or order.screen_title
        self.header.seller = self.header.seller or order.seller
        self.header.jihuanshe_order_id = (
            self.header.jihuanshe_order_id or order.jihuanshe_order_id
        )
        self.header.purchase_date = self.header.purchase_date or order.purchase_date
        self.header.express_company = self.header.express_company or order.express_company
        self.header.express_tracking = self.header.express_tracking or order.express_tracking

        if self.declared is None:
            self.declared = order.declared_item_count
        if self.screen_title is None:
            self.screen_title = order.screen_title

        if order.reached_footer:
            self.footer["reached"] = True
            self.footer["domestic_shipping_fen"] = (
                self.footer["domestic_shipping_fen"] or order.domestic_shipping_fen
            )
            self.footer["subtotal_fen"] = self.footer["subtotal_fen"] or order.subtotal_fen
            self.footer["total_paid_fen"] = self.footer["total_paid_fen"] or order.total_paid_fen

        if with_items:
            self._ingest_items(order, shot)

    def _ingest_items(self, order: ParsedOrder, shot: bytes | None) -> None:
        old_len = len(self.items)
        merged, _overlap = merge_items(self.items, order.items)
        self.items = merged

        # Crop the genuinely-new items (appended tail) that are cleanly visible.
        for offset, item in enumerate(merged[old_len:]):
            if item.image_bounds and shot and order.screen_size:
                filename = image_filename(item, old_len + offset)
                out_path = self.images_dir / filename
                if crop_if_clean(
                    shot, item.image_bounds, order.screen_size, order.occlusions, out_path
                ):
                    item.image_path = f"{self.rel_dir}/{filename}"

        # Any visible card may complete an image missed on an earlier screen.
        # Do not limit this to the exact sequence overlap: viewport clipping can
        # make the parser omit a neighbouring row from one of the two dumps.
        if shot and order.screen_size:
            missing_by_identity: dict[tuple, list[tuple[int, Any]]] = {}
            for acc_index, acc_item in enumerate(self.items):
                if acc_item.image_path is None:
                    missing_by_identity.setdefault(item_fingerprint(acc_item), []).append(
                        (acc_index, acc_item)
                    )

            for visible_item in order.items:
                candidates = missing_by_identity.get(item_fingerprint(visible_item), [])
                if not candidates or not visible_item.image_bounds:
                    continue
                for acc_index, acc_item in candidates:
                    filename = image_filename(acc_item, acc_index)
                    out_path = self.images_dir / filename
                    if crop_if_clean(
                        shot,
                        visible_item.image_bounds,
                        order.screen_size,
                        order.occlusions,
                        out_path,
                    ):
                        acc_item.image_path = f"{self.rel_dir}/{filename}"
                missing_by_identity.pop(item_fingerprint(visible_item), None)

    @property
    def total_qty(self) -> int:
        return sum(item.quantity for item in self.items)

    def snapshot(self) -> dict[str, Any]:
        image_count = sum(item.image_path is not None for item in self.items)
        return {
            "session_id": self.session_id,
            "items": len(self.items),
            "images": image_count,
            "total_qty": self.total_qty,
            "declared": self.declared,
            "reached_footer": self.footer["reached"],
            "total_captured": self.footer["total_paid_fen"] is not None,
            "complete": self.declared is not None and self.total_qty == self.declared,
            "images_complete": bool(self.items) and image_count == len(self.items),
        }

    def to_preview(self) -> CapturePreview:
        warnings = list(self.warnings)
        if self.declared is not None:
            if self.total_qty == self.declared:
                pass
            elif len(self.items) == self.declared:
                warnings.append(
                    f"coincide por líneas: {len(self.items)} líneas == {self.declared} declaradas"
                )
            else:
                warnings.append(
                    f"recuento no coincide: {self.total_qty} cartas en {len(self.items)} "
                    f"líneas, declaradas {self.declared}"
                )

        order = ParsedOrder(
            screen_title=self.header.screen_title or self.screen_title,
            has_product_info=True,
            declared_item_count=self.declared,
            seller=self.header.seller,
            jihuanshe_order_id=self.header.jihuanshe_order_id,
            purchase_date=self.header.purchase_date,
            express_company=self.header.express_company,
            express_tracking=self.header.express_tracking,
            domestic_shipping_fen=self.footer["domestic_shipping_fen"],
            subtotal_fen=self.footer["subtotal_fen"],
            total_paid_fen=self.footer["total_paid_fen"],
            reached_footer=self.footer["reached"],
            items=self.items,
        )
        return CapturePreview(
            detected=True,
            session_id=self.session_id,
            screen_title=order.screen_title,
            declared_item_count=self.declared,
            order=order,
            raw_dumps=self.dumps,
            warnings=warnings,
        )


def start_session(settings: Settings) -> CaptureSession:
    session_id = uuid.uuid4().hex
    images_dir = settings.images_dir / "preview" / session_id
    images_dir.mkdir(parents=True, exist_ok=True)
    return CaptureSession(session_id, settings, images_dir)
