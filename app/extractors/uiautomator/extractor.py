"""UIAutomator extractor for detection and automatic order capture."""
from __future__ import annotations

import time

from app.config import Settings
from app.extractors.contract import CapturePreview, CaptureStatus
from app.extractors.session import CaptureSession, start_session
from app.extractors.uiautomator.merge import item_fingerprint
from app.extractors.uiautomator.order_list import parse_order_list
from app.extractors.uiautomator.parse import parse_window_xml


class UIAutomatorExtractor:
    def __init__(self, adb, settings: Settings):
        self.adb = adb
        self.settings = settings

    def _adb_ok(self) -> bool:
        try:
            return self.adb.available()
        except Exception:
            return False

    def status(self) -> CaptureStatus:
        if not self._adb_ok():
            return CaptureStatus(detected=False, error="ADB no disponible o sin dispositivo")
        xml = self.adb.current_window_xml()
        if not xml:
            return CaptureStatus(detected=False, error="No se pudo obtener el dump de la ventana")
        order = parse_window_xml(xml)
        detected = order.has_product_info or order.screen_title is not None
        return CaptureStatus(
            detected=detected,
            available=True,
            screen_title=order.screen_title,
            declared_item_count=order.declared_item_count,
        )

    def capture_current(
        self, *, with_image: bool = True, verify_image: bool = True
    ) -> tuple[str | None, bytes | None]:
        """One stable dump + screenshot of the current screen (no scrolling).

        Recycler views can finish a scroll between the UI dump and screencap.
        In that case the bitmap belongs to different rows and images become
        attached to the wrong cards. Verify the visible item sequence after
        the screencap and retry instead of accepting a mismatched pair.
        """
        xml = self.adb.current_window_xml()
        if not with_image or not self.settings.capture_images or not xml:
            return xml, None

        if not verify_image:
            return xml, self.adb.screenshot_bytes()

        for _ in range(3):
            shot = self.adb.screenshot_bytes()
            verification_xml = self.adb.current_window_xml()
            if shot and verification_xml and self._same_visible_items(xml, verification_xml):
                return verification_xml, shot
            xml = verification_xml
            if not xml:
                break
        return xml, None

    @staticmethod
    def _same_visible_items(before_xml: str, after_xml: str) -> bool:
        before = parse_window_xml(before_xml).items
        after = parse_window_xml(after_xml).items
        return [(item_fingerprint(item), item.image_bounds) for item in before] == [
            (item_fingerprint(item), item.image_bounds) for item in after
        ]

    def preview(self, auto_scroll: bool = False) -> CapturePreview:
        """Capture the current order.

        ``auto_scroll=False`` captures a single screen (manual mode building
        block). ``auto_scroll=True`` seeks up to the header (seller, order id,
        purchase date), then drives the scroll down through the items to the
        footer.
        """
        if not self._adb_ok():
            return CapturePreview(detected=False, error="ADB no disponible o sin dispositivo")

        session = start_session(self.settings)

        # Ingest the first viewport for its header/screen metadata only. Items
        # are captured in a single downward pass so the positional merge stays
        # consistent; the header seek and item pass must not interleave.
        xml, shot = self.capture_current(verify_image=False)
        if not xml:
            return session.to_preview()
        session.ingest(xml, shot, with_items=not auto_scroll)

        if auto_scroll:
            self._scroll_to_header(session)
            self._scroll_to_bottom(session)

        return session.to_preview()

    def visible_listed_orders(self):
        xml = self.adb.current_window_xml()
        return parse_order_list(xml or "")

    def open_listed_order(self, listed_order) -> bool:
        left, top, right, bottom = listed_order.bounds
        # The card body handles the click; the centre column avoids avatar and
        # action buttons nested at the sides.
        self.adb.tap((left + right) // 2, (top + bottom) // 2)
        for _ in range(15):
            time.sleep(0.2)
            status = self.status()
            if status.detected:
                return True
        return False

    def return_to_order_list(self) -> bool:
        self.adb.back()
        for _ in range(15):
            time.sleep(0.2)
            if self.visible_listed_orders():
                return True
        return False

    def scroll_order_list(self) -> None:
        self.adb.swipe_order_list_up()
        time.sleep(0.7)

    def _scroll_to_header(self, session: CaptureSession) -> None:
        """Scroll up to the order header to capture seller, order id and date."""
        prev_xml: str | None = None
        stuck = 0
        for _ in range(self.settings.max_scrolls):
            if (
                session.header.seller
                and session.header.jihuanshe_order_id
                and session.header.purchase_date
            ):
                break
            self.adb.swipe_down()
            time.sleep(0.2)
            xml, _shot = self.capture_current(with_image=False)
            if not xml:
                break
            if xml == prev_xml:
                stuck += 1
                if stuck >= 2:
                    break
            else:
                stuck = 0
            prev_xml = xml
            session.ingest(xml, None, with_items=False)

    def _scroll_to_bottom(self, session: CaptureSession) -> None:
        prev_xml: str | None = None
        stuck = 0
        for _ in range(self.settings.max_scrolls):
            # Auto-scroll owns the device position, so the preceding settle
            # delay makes the extra verification dump unnecessary.
            xml, shot = self.capture_current(verify_image=False)
            if not xml:
                break
            session.ingest(xml, shot)
            images_ready = (
                not self.settings.capture_images or session.snapshot()["images_complete"]
            )
            if (
                session.footer["reached"]
                and session.footer["total_paid_fen"] is not None
                and images_ready
            ):
                break
            if xml == prev_xml:
                stuck += 1
                if stuck >= 2:
                    session.warnings.append("fin de lista (sin progreso)")
                    break
            else:
                stuck = 0
            prev_xml = xml
            self.adb.swipe_up()
            time.sleep(0.2)
