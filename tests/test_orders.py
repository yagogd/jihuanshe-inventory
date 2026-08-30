from app.domain.orders import suggest_alipay_fee


def test_alipay_fee_above_threshold_whole_payment():
    # 250.00 + 15.00 = 265.00 -> 3% of 265 = 7.95 -> 795 fen
    assert suggest_alipay_fee(25000, 1500, 20000, 0.03) == 795


def test_alipay_fee_below_threshold_is_zero():
    # 150.00 + 40.00 = 190.00 <= 200 -> 0
    assert suggest_alipay_fee(15000, 4000, 20000, 0.03) == 0


def test_alipay_fee_exactly_threshold_is_zero():
    assert suggest_alipay_fee(20000, 0, 20000, 0.03) == 0
