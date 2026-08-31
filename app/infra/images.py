"""Filesystem image helpers shared by the domain and import flows."""
from __future__ import annotations

import shutil
from pathlib import Path


def relocate_images(images_dir: Path, order_id: str, items: list) -> None:
    """Move preview crops into a per-order directory and update ``image_path``.

    Items are plain objects with a mutable ``image_path`` attribute (``str``
    relative to ``images_dir``, or ``None``). Source files that no longer exist
    have their path cleared.
    """
    target = images_dir / order_id
    target.mkdir(parents=True, exist_ok=True)
    for index, item in enumerate(items):
        if not item.image_path:
            continue
        source = images_dir / item.image_path
        if source.exists():
            destination = target / f"{index:03d}.jpg"
            shutil.move(str(source), str(destination))
            item.image_path = f"{order_id}/{destination.name}"
        else:
            item.image_path = None
