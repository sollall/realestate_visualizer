from load import validate_data

def test_validate_data():
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
    
    assert validate_data(valid_data) == True, "Valid data should return True"
    assert validate_data(invalid_data) == False, "Invalid data should return False"

if __name__ == "__main__":
    test_validate_data()
    print("All tests passed.")