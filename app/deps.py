"""Dependency providers (override-able in tests)."""
from __future__ import annotations

from app.config import get_settings
from app.extractors.uiautomator.adb import AdbClient
from app.extractors.uiautomator.extractor import UIAutomatorExtractor

_extractor: UIAutomatorExtractor | None = None


def get_extractor() -> UIAutomatorExtractor:
    global _extractor
    if _extractor is None:
        settings = get_settings()
        _extractor = UIAutomatorExtractor(AdbClient(settings.adb_path), settings)
    return _extractor
