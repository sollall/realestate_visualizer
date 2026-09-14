"""国土数値情報(鉄道 N02)の路線・駅データをdata/rawdata/railway/へ保存するスクリプト。

pages側の地図に路線・駅を重ねて表示するための元データを用意する。
取得したGeoJSONはそのままpydeckのGeoJsonLayerに渡せる。

使い方:
    python scripts/fetch_railway_data.py
    python scripts/fetch_railway_data.py --year-code 24

--year-codeは国土数値情報の配布ページ
(https://nlftp.mlit.go.jp/ksj/gml/datalist/KsjTmplt-N02-<年>.html)に記載の
zipファイル名(例: 令和5年度データならN02-23_GML.zip)の数字部分。
"""

import argparse
import sys
from pathlib import Path

# scripts/配下から直接実行された場合でもリポジトリルート直下のextractパッケージを
# importできるよう、リポジトリルートをsys.pathへ明示的に追加する。
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from extract.railway import fetch_railway_geojson

DEFAULT_YEAR_CODE = "23"
DEFAULT_OUTPUT_DIR = Path("data/rawdata/railway")


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--year-code", default=DEFAULT_YEAR_CODE, help="国土数値情報の年度コード(例: 23)")
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR), help="保存先ディレクトリ")
    args = parser.parse_args()

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"fetching N02-{args.year_code}_GML.zip ...")
    geojson_files = fetch_railway_geojson(args.year_code)

    if not geojson_files:
        print(
            "GeoJSONファイルがzip内に見つかりませんでした。"
            "--year-codeの値や配布元のzip構成が変わっていないか確認してください。",
            file=sys.stderr,
        )
        sys.exit(1)

    for name, content in geojson_files.items():
        # zip内はディレクトリ付きの場合があるのでファイル名部分だけ使う
        dest = output_dir / Path(name).name
        dest.write_bytes(content)
        print(f"saved: {dest} ({len(content):,} bytes)")


if __name__ == "__main__":
    main()
