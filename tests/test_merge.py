from app.extractors.contract import ParsedItem
from app.extractors.uiautomator.merge import merge_items


def _item(name, num, price=1000, qty=1):
    return ParsedItem(
        raw_name=name, set_code="SET", collector_number=num, quantity=qty, unit_price_fen=price
    )


def test_empty_acc_returns_new():
    new = [_item("A", "001")]
    merged, overlap = merge_items([], new)
    assert merged == new
    assert overlap == 0


def test_overlap_appends_only_new():
    acc = [_item("A", "001"), _item("B", "002"), _item("C", "003")]
    new = [_item("B", "002"), _item("C", "003"), _item("D", "004")]
    merged, overlap = merge_items(acc, new)
    assert overlap == 2
    assert [x.raw_name for x in merged] == ["A", "B", "C", "D"]


def test_duplicate_identical_lines_kept():
    acc = [_item("A", "001"), _item("A", "001"), _item("B", "002")]
    new = [_item("A", "001"), _item("B", "002"), _item("C", "003")]
    merged, overlap = merge_items(acc, new)
    assert overlap == 2
    assert [x.raw_name for x in merged] == ["A", "A", "B", "C"]


def test_no_overlap():
    acc = [_item("A", "001")]
    new = [_item("Z", "099")]
    merged, overlap = merge_items(acc, new)
    assert overlap == 0
    assert len(merged) == 2
