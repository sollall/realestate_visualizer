# extractとかtransformとかを一括でやる
import sys
from datetime import datetime

from pipelines.mansionreview import MansionReviewPipeline
from pipelines.suumo import SuumoPipeline

# サイト名と対応するパイプラインをマッピング
PIPELINES = {
    "mansionreview": MansionReviewPipeline,
    "suumo": SuumoPipeline,
}

def main(site_name):
    if site_name not in PIPELINES:
        raise ValueError(f"Error: Unknown site '{site_name}'. Available sites: {list(PIPELINES.keys())}")

    now = datetime.now()
    pipeline = PIPELINES[site_name]()

    result = pipeline.extract()
    result.to_csv(now.strftime(f"data/rawdata/activelist/{site_name}_%Y%m%d.csv"))

    transformed = pipeline.transform(result)

    if not pipeline.validate(transformed):
        raise ValueError(f"Data from {site_name} is invalid.")

    print(f"Data from {site_name} is valid.")
    transformed.to_csv(now.strftime(f"data/analytics/activelist/{site_name}_%Y%m%d.csv"))

if __name__ == "__main__":
    # コマンドライン引数からサイト名を取得
    if len(sys.argv) != 2:
        raise ValueError("Usage: python load.py <site_name>")

    site_name = sys.argv[1]

    main(site_name)
