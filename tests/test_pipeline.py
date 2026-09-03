import pandas as pd

from pipelines.suumo import SuumoPipeline


def test_validate_raw():
    pipeline = SuumoPipeline()

    # 正常なデータ
    valid_data = {
        "name": "Test Mansion",
        "price": 50000000,
        "address": "Tokyo, Japan",
        "area": 100.0,
        "age": 5,
        "age_months": 6
    }

    # 不正なデータ（カラムが不足）
    invalid_data = {
        "name": "Test Mansion",
        "price": 50000000,
        "address": "Tokyo, Japan",
        "area": 100.0
    }

    assert pipeline.validate_raw(valid_data) == True, "Valid data should return True"
    assert pipeline.validate_raw(invalid_data) == False, "Invalid data should return False"


def test_validate_raw_rejects_empty_dataframe():
    """スクレイピング先のHTML構造が変わるなどしてextractが0件を返した場合を検知できること"""
    pipeline = SuumoPipeline()

    empty_data = pd.DataFrame(columns=["name", "price", "address", "area", "age"])

    assert pipeline.validate_raw(empty_data) == False, "Empty dataframe should return False"


def test_validate_raw_rejects_dataframe_with_null_required_column():
    """必須カラムがnull埋めされている(パース失敗など)場合を検知できること"""
    pipeline = SuumoPipeline()

    data_with_null = pd.DataFrame({
        "name": ["Test Mansion"],
        "price": [50000000],
        "address": ["Tokyo, Japan"],
        "area": [100.0],
        "age": [None],
    })

    assert pipeline.validate_raw(data_with_null) == False, "Null in required column should return False"


def test_validate_raw_accepts_valid_dataframe():
    pipeline = SuumoPipeline()

    valid_data = pd.DataFrame({
        "name": ["Test Mansion"],
        "price": [50000000],
        "address": ["Tokyo, Japan"],
        "area": [100.0],
        "age": [5],
    })

    assert pipeline.validate_raw(valid_data) == True, "Valid dataframe should return True"
