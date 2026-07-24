import pandas as pd

from pipeline import SuumoPipeline


def test_validate():
    pipeline = SuumoPipeline()

    # 正常なデータ
    valid_data = pd.DataFrame({
        "address": ["Tokyo, Japan"],
        "area": [100.0],
        "age": [5],
        "lons": [139.7],
        "lats": [35.6],
        "坪単価": [300.0],
    })

    # 不正なデータ（カラムが不足）
    invalid_data = pd.DataFrame({
        "address": ["Tokyo, Japan"],
        "area": [100.0],
    })

    assert pipeline.validate(valid_data) == True, "Valid data should return True"
    assert pipeline.validate(invalid_data) == False, "Invalid data should return False"

if __name__ == "__main__":
    test_validate()
    print("All tests passed.")
