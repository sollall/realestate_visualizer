"""extract/suumo.pyの価格・築年のパースが、価格未定や未完成の新築を
0円・負の築年数として紛れ込ませないことを確認するテスト。"""

from datetime import datetime

import pandas as pd

import extract.suumo as suumo


def test_extract_price_parses_oku_and_man():
    assert suumo.extract_price("1億2000万円") == 120000000
    assert suumo.extract_price("2億円") == 200000000
    assert suumo.extract_price("4980万円") == 49800000


def test_extract_price_ignores_leading_text_and_commas():
    assert suumo.extract_price("予定価格 1,980万円") == 19800000


def test_extract_price_uses_lower_bound_of_range():
    assert suumo.extract_price("5000万円～6000万円") == 50000000


def test_extract_price_returns_none_when_undecided():
    assert suumo.extract_price("価格未定") is None


def test_calculate_age():
    now = datetime(2026, 9, 1)
    assert suumo.calculate_age("2000年3月", now) == (26, 6)
    assert suumo.calculate_age("2000年12月", now) == (25, 9)


def test_calculate_age_returns_none_for_future_build():
    assert suumo.calculate_age("2027年3月予定", datetime(2026, 9, 1)) == (None, None)


def test_drop_unparsable_removes_rows_with_missing_values():
    data = pd.DataFrame({
        "name": ["A", "B", "C"],
        "price": [50000000, None, 30000000],
        "address": ["x", "y", "z"],
        "area": [70.0, 60.0, 50.0],
        "age": [10, 5, None],
        "age_months": [1, 2, None],
    })

    parsed = suumo.drop_unparsable(data)

    assert parsed["name"].tolist() == ["A"]
