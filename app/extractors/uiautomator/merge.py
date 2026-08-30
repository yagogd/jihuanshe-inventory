"""Merge items parsed from consecutive dumps.

Deduplication is positional, not set-based: the same card can legitimately
appear twice as two distinct lines. We detect the overlap between the tail of
the accumulated list and the head of the new dump and append only the new part.
"""
from __future__ import annotations

from app.extractors.contract import ParsedItem


def item_fingerprint(item: ParsedItem) -> tuple:
    return (
        item.set_code,
        item.collector_number,
        item.raw_name,
        item.variant,
        item.quantity,
        item.unit_price_fen,
        item.language,
    )


def merge_items(acc: list[ParsedItem], new: list[ParsedItem]) -> tuple[list[ParsedItem], int]:
    """Return (merged_list, overlap_size)."""
    if not acc:
        return list(new), 0

    fp_acc = [item_fingerprint(x) for x in acc]
    fp_new = [item_fingerprint(x) for x in new]

    overlap = 0
    max_overlap = min(len(acc), len(new))
    for candidate in range(max_overlap, 0, -1):
        if fp_acc[-candidate:] == fp_new[:candidate]:
            overlap = candidate
            break

    return acc + new[overlap:], overlap
