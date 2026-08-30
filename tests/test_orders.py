from pathlib import Path

from app.config import Settings
from app.domain.orders import suggest_alipay_fee


def _settings():
    return Settings(
        adb_path="adb",
        data_dir=Path("."),
        alipay_fee_threshold_fen=20000,
        alipay_fee_rate=0.03,
        fx_cny_eur=0.13,
        capture_images=False,
        max_scrolls=80,
    )


def test_alipay_fee_above_threshold_whole_payment():
    # 250.00 + 15.00 = 265.00 -> 3% of 265 = 7.95 -> 795 fen
    assert suggest_alipay_fee(25000, 1500, _settings()) == 795


def test_alipay_fee_below_threshold_is_zero():
    # 150.00 + 40.00 = 190.00 <= 200 -> 0
    assert suggest_alipay_fee(15000, 4000, _settings()) == 0


def test_alipay_fee_exactly_threshold_is_zero():
    assert suggest_alipay_fee(20000, 0, _settings()) == 0
