"""Card images: crop from a window screenshot using the ImageView bounds.

Priority per plan is a real card identifier; UIAutomator gives us no image URL,
so we fall back to cropping the ``com.jihuanshe:id/image`` bounds out of a
full-window screenshot. We never keep the full screenshot as the card image.
"""
from __future__ import annotations

import io
import re
from pathlib import Path

from PIL import Image

from app.extractors.contract import ParsedItem

CROP_PADDING = 8
# The Jihuanshe card ImageView is roughly 1.40 times as tall as it is wide.
# UIAutomator clips bounds at the viewport edge, so checking only the screen
# coordinates is not enough to detect a card that is partially visible.
MIN_CARD_ASPECT_RATIO = 1.35


def crop_bounds(
    screenshot_bytes: bytes,
    bounds: tuple[int, int, int, int],
    out_abs_path: Path,
) -> bool:
    try:
        image = Image.open(io.BytesIO(screenshot_bytes))
    except Exception:
        return False

    x1, y1, x2, y2 = bounds
    x1 = max(0, min(x1, image.width))
    x2 = max(0, min(x2, image.width))
    y1 = max(0, min(y1, image.height))
    y2 = max(0, min(y2, image.height))
    if x2 <= x1 or y2 <= y1:
        return False
    if (y2 - y1) / (x2 - x1) < MIN_CARD_ASPECT_RATIO:
        return False

    out_abs_path.parent.mkdir(parents=True, exist_ok=True)
    image.crop((x1, y1, x2, y2)).convert("RGB").save(out_abs_path, "JPEG", quality=90)
    return True


def _overlaps(a: tuple[int, int, int, int], b: tuple[int, int, int, int]) -> bool:
    ax1, ay1, ax2, ay2 = a
    bx1, by1, bx2, by2 = b
    return not (ax2 <= bx1 or bx2 <= ax1 or ay2 <= by1 or by2 <= ay1)


def crop_if_clean(
    screenshot_bytes: bytes,
    bounds: tuple[int, int, int, int],
    screen_size: tuple[int, int] | None,
    occlusions: list[tuple[int, int, int, int]],
    out_abs_path: Path,
) -> bool:
    """Crop only if the image is fully on-screen and not covered by an overlay.

    Cards scrolled to the edge of the screen (or hidden behind the 查看评价
    button) produce bad crops; we skip those and crop them later when they are
    cleanly visible. A small padding is added around the crop so the card art
    is not clipped at the edges.
    """
    if screen_size is None:
        return False
    width, height = screen_size
    x1, y1, x2, y2 = bounds
    if x1 < 0 or y1 < 0 or x2 > width or y2 > height:
        return False
    if x2 <= x1 or y2 <= y1:
        return False
    for occlusion in occlusions:
        if _overlaps(bounds, occlusion):
            return False

    px1 = max(0, x1 - CROP_PADDING)
    py1 = max(0, y1 - CROP_PADDING)
    px2 = min(width, x2 + CROP_PADDING)
    py2 = min(height, y2 + CROP_PADDING)
    return crop_bounds(screenshot_bytes, (px1, py1, px2, py2), out_abs_path)


def _slugify(text: str | None) -> str:
    if not text:
        return ""
    slug = re.sub(r"[^A-Za-z0-9]+", "-", text.strip())
    return slug.strip("-")


def image_filename(item: ParsedItem, index: int) -> str:
    parts = [str(index)]
    for value in (item.set_code, item.collector_number, item.variant):
        slug = _slugify(value)
        if slug:
            parts.append(slug)
    return "-".join(parts) + ".jpg"
