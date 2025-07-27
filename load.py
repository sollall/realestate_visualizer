# extractとかtransformとかを一括でやる
import sys
from datetime import datetime
import extract.mansionreview as extract_mansionreview
import extract.suumo as extract_suumo

import transform.mansionreview as transform_mansionreview
import transform.suumo as transform_suumo

# サイト名と対応する関数をマッピング
EXTRACT_FUNCTIONS = {
    "mansionreview": extract_mansionreview.scrap_estate_data,
    "suumo": extract_suumo.get_estate_data,
}

TRANSFORM_FUNCTIONS = {
    "mansionreview": transform_mansionreview.transform,
}

def validate_data(data):
    """
    データの検証関数
    ここでは、データが空でないことを確認する簡単な検証を行う。
    必要に応じて、より詳細な検証を追加できます。
    """

    #dataのカラムに必要なカラムを定義
    # 例: 必要なカラムが存在するかどうかを確認
    val_columns = ["name", "price", "address", "area", "age"]
    if not all(col in data for col in val_columns):
        return False

    return True

def main(site_name):
    # サイト名に対応する関数を呼び出す
    now = datetime.now()

    if site_name in EXTRACT_FUNCTIONS:
        result = EXTRACT_FUNCTIONS[site_name]()
    else:
        raise ValueError(f"Error: Unknown site '{site_name}'. Available sites: {list(EXTRACT_FUNCTIONS.keys())}")

    if validate_data(result):
        print(f"Data from {site_name} is valid.")
    else:
        raise ValueError(f"Data from {site_name} is invalid.")
    
    result.to_csv(now.strftime("data/rawdata/activelist/mansionreview_%Y%m%d.csv"))

    if site_name in TRANSFORM_FUNCTIONS:
        transformed = TRANSFORM_FUNCTIONS[site_name](result)
    else:
        raise ValueError(f"TransformError: Unknown site '{site_name}'. Available sites: {list(TRANSFORM_FUNCTIONS.keys())}")

    transformed.to_csv(now.strftime("data/analytics/activelist/mansionreview_%Y%m%d.csv"))

if __name__ == "__main__":
    # コマンドライン引数からサイト名を取得
    if len(sys.argv) != 2:
        raise ValueError("Usage: python load.py <site_name>")
    
    site_name = sys.argv[1]
    
    main(site_name)


    
    

