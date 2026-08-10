# extractとかtransformとかを一括でやる
import sys
from datetime import datetime

from sites import SITE_CLASSES

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
    # サイト名に対応するクラスを呼び出す
    now = datetime.now()

    if site_name not in SITE_CLASSES:
        raise ValueError(f"Error: Unknown site '{site_name}'. Available sites: {list(SITE_CLASSES.keys())}")

    site = SITE_CLASSES[site_name]()

    result = site.extract()

    if validate_data(result):
        print(f"Data from {site_name} is valid.")
    else:
        raise ValueError(f"Data from {site_name} is invalid.")

    result.to_csv(now.strftime(f"data/rawdata/activelist/{site_name}_%Y%m%d.csv"))

    transformed = site.transform(result)

    transformed.to_csv(now.strftime(f"data/analytics/activelist/{site_name}_%Y%m%d.csv"))

if __name__ == "__main__":
    # コマンドライン引数からサイト名を取得
    if len(sys.argv) != 2:
        raise ValueError("Usage: python load.py <site_name>")
    
    site_name = sys.argv[1]
    
    main(site_name)


    
    

