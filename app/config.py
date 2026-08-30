"""Configuration and runtime settings.

Everything here is read once and cached. No device-specific or business
logic lives here beyond defaults that can be overridden via environment
variables.
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent


def _default_adb_path() -> str:
    candidates = [
        os.environ.get("JIHUANSHE_ADB"),
        str(PROJECT_ROOT / "platform-tools" / "adb.exe"),
    ]
    for candidate in candidates:
        if candidate and Path(candidate).exists():
            return candidate
    return "adb"


@dataclass(frozen=True)
class Settings:
    adb_path: str
    data_dir: Path
    alipay_fee_threshold_fen: int
    alipay_fee_rate: float
    fx_cny_eur: float
    capture_images: bool
    max_scrolls: int

    @property
    def images_dir(self) -> Path:
        return self.data_dir / "images"

    @property
    def dumps_dir(self) -> Path:
        return self.data_dir / "dumps"

    @property
    def db_path(self) -> Path:
        return self.data_dir / "app.db"


@lru_cache
def get_settings() -> Settings:
    data_dir = Path(os.environ.get("JIHUANSHE_DATA_DIR", PROJECT_ROOT / "data"))
    data_dir.mkdir(parents=True, exist_ok=True)
    (data_dir / "images").mkdir(parents=True, exist_ok=True)
    (data_dir / "dumps").mkdir(parents=True, exist_ok=True)

    return Settings(
        adb_path=_default_adb_path(),
        data_dir=data_dir,
        alipay_fee_threshold_fen=int(os.environ.get("JIHUANSHE_ALIPAY_THRESHOLD_FEN", 20000)),
        alipay_fee_rate=float(os.environ.get("JIHUANSHE_ALIPAY_RATE", 0.03)),
        fx_cny_eur=float(os.environ.get("JIHUANSHE_FX_CNY_EUR", 0.13)),
        capture_images=os.environ.get("JIHUANSHE_CAPTURE_IMAGES", "1") not in ("0", "false", "False"),
        max_scrolls=int(os.environ.get("JIHUANSHE_MAX_SCROLLS", 80)),
    )
