# extractとかtransformとかを一括でやる
import sys
from datetime import datetime
from extract import mansionreview, suumo, utils

# サイト名と対応する関数をマッピング
EXTRACT_FUNCTIONS = {
    "mansionreview": mansionreview.scrap_estate_data,
    "suumo": suumo.get_estate_data,
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

    lons,lats=utils.get_lat_lon(result["address"].values)
    result["lons"]=lons
    result["lats"]=lats

    result.to_csv(now.strftime("data/analytics/activelist/mansionreview_%Y%m%d.csv"))

if __name__ == "__main__":
    # コマンドライン引数からサイト名を取得
    if len(sys.argv) != 2:
        raise ValueError("Usage: python load.py <site_name>")
    
    site_name = sys.argv[1]
    
    main(site_name)


    
    

