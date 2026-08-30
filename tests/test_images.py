import io

from PIL import Image

from app.extractors.contract import ParsedItem
from app.extractors.uiautomator.images import (
    crop_bounds,
    crop_if_clean,
    image_filename,
    relocate_images,
)


def _png(size=(100, 100), color=(255, 0, 0)):
    image = Image.new("RGB", size, color)
    buf = io.BytesIO()
    image.save(buf, "PNG")
    return buf.getvalue()


def test_crop_bounds(tmp_path):
    out = tmp_path / "out.jpg"
    assert crop_bounds(_png(), (10, 10, 60, 60), out) is True
    assert out.exists()
    assert Image.open(out).size == (50, 50)


def test_crop_clamped_to_image(tmp_path):
    out = tmp_path / "out.jpg"
    assert crop_bounds(_png(), (-5, -5, 500, 500), out) is True
    assert Image.open(out).size == (100, 100)


def test_crop_empty_returns_false(tmp_path):
    out = tmp_path / "out.jpg"
    assert crop_bounds(_png(), (0, 0, 0, 0), out) is False
    assert not out.exists()


def test_crop_if_clean_rejects_offscreen(tmp_path):
    out = tmp_path / "out.jpg"
    assert crop_if_clean(_png(), (-5, -5, 50, 50), (100, 100), [], out) is False
    assert crop_if_clean(_png(), (60, 60, 200, 200), (100, 100), [], out) is False


def test_crop_if_clean_rejects_viewport_clipped_card(tmp_path):
    out = tmp_path / "out.jpg"
    # UIAutomator may clamp a partially visible 50x70 card to only 50x40.
    assert crop_if_clean(_png(), (20, 0, 70, 40), (100, 100), [], out) is False


def test_crop_if_clean_rejects_occluded(tmp_path):
    out = tmp_path / "out.jpg"
    # image overlaps the 查看评价 overlay at the bottom
    occlusions = [(10, 60, 90, 100)]
    assert crop_if_clean(_png(), (20, 40, 80, 80), (100, 100), occlusions, out) is False


def test_crop_if_clean_crops_when_clear(tmp_path):
    out = tmp_path / "out.jpg"
    assert crop_if_clean(_png(), (20, 10, 60, 80), (100, 100), [], out) is True
    # 40x70 original + 8px padding on each side -> 56x86
    assert Image.open(out).size == (56, 86)


def test_image_filename_uses_identity():
    item = ParsedItem(raw_name="x", set_code="OGN", collector_number="078/298", variant="Promo")
    assert image_filename(item, 0) == "0-OGN-078-298-Promo.jpg"


def test_relocate_images(tmp_path):
    images = tmp_path / "images"
    preview = images / "preview" / "sess"
    preview.mkdir(parents=True)
    (preview / "0-x.jpg").write_bytes(b"jpeg")

    class Item:
        pass

    a = Item()
    a.image_path = "preview/sess/0-x.jpg"
    b = Item()
    b.image_path = "missing.jpg"

    relocate_images(images, "order1", [a, b])

    assert a.image_path == "order1/000.jpg"
    assert (images / "order1" / "000.jpg").exists()
    assert b.image_path is None
