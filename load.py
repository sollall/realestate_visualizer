# extractとtransformを一括で実行するCLIエントリポイント
import sys
from datetime import datetime

from pipelines.registry import PIPELINES


def main(site_name):
    if site_name not in PIPELINES:
        raise ValueError(f"Error: Unknown site '{site_name}'. Available sites: {list(PIPELINES.keys())}")

    pipeline = PIPELINES[site_name]()
    now = datetime.now()

    result = pipeline.extract()
    if not pipeline.validate_raw(result):
        raise ValueError(f"Data from {site_name} is invalid.")
    print(f"Data from {site_name} is valid.")

    result.to_csv(now.strftime(f"data/rawdata/activelist/{site_name}_%Y%m%d.csv"))

    transformed = pipeline.transform(result)
    transformed.to_csv(now.strftime(f"data/analytics/activelist/{site_name}_%Y%m%d.csv"))


if __name__ == "__main__":
    # コマンドライン引数からサイト名を取得
    if len(sys.argv) != 2:
        raise ValueError("Usage: python load.py <site_name>")

    site_name = sys.argv[1]

    main(site_name)
