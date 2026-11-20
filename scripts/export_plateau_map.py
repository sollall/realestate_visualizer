"""物件CSVとPLATEAUの3D建物を重ねたMachGLの地図を単体HTMLに書き出すスクリプト。

streamlitを使わず、書き出したHTMLをブラウザで開くだけで地図を見られる。
データ・区の切り替えや建物の不透明度はページ内のパネルで変更でき、
操作のたびに地図を読み込み直すことはない。

使い方:
    python scripts/export_plateau_map.py
    python -m http.server -d data/maps 8000   # http://localhost:8000/plateau_machgl.html を開く

GeoloniaのデモキーはHTMLファイルを直接開いた状態(file://)では使えないため、
上のようにlocalhostで配信して開く。GitHub Pagesなどにそのまま置いても表示できる。
独自ドメインで公開する場合は、Geoloniaで発行したAPIキーを--api-keyか
環境変数GEOLONIA_API_KEYで指定する。
"""

import argparse
import os
import sys
from pathlib import Path

# scripts/配下から直接実行された場合でもリポジトリルート直下のanalysisパッケージを
# importできるよう、リポジトリルートをsys.pathへ明示的に追加する。
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from analysis.colors import scale_color
from analysis.loader import list_csv_files, load_csv
from analysis.machgl import DEFAULT_WARD, DEMO_API_KEY, WARD_CENTERS, build_map_html, to_geojson

TARGET_FOLDER = "activelist"
DEFAULT_OUTPUT = Path("data/maps/plateau_machgl.html")


def build_datasets(folder):
    """`data/analytics/<folder>/`配下の物件CSVをすべて{ファイル名: GeoJSON}にする。"""
    datasets = {}
    for filename in sorted(list_csv_files(folder)):
        dataframe = load_csv(folder, filename)
        dataframe["color"] = dataframe["坪単価"].apply(scale_color)
        if "階数" not in dataframe.columns:
            dataframe["階数"] = None
        datasets[filename] = to_geojson(dataframe, ["address", "坪単価", "階数", "color"])
    return datasets


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT), help="書き出すHTMLのパス")
    parser.add_argument("--ward", default=DEFAULT_WARD, choices=list(WARD_CENTERS), help="最初に表示する区")
    parser.add_argument("--api-key", default=os.environ.get("GEOLONIA_API_KEY", DEMO_API_KEY),
                        help="GeoloniaのAPIキー(未指定ならlocalhost等でのみ使えるデモキー)")
    args = parser.parse_args()

    datasets = build_datasets(TARGET_FOLDER)
    if not datasets:
        print(f"data/analytics/{TARGET_FOLDER}/ に物件CSVがありません。先に load.py でデータを取得してください。")
        sys.exit(1)

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(build_map_html(datasets, api_key=args.api_key, initial_ward=args.ward), encoding="utf-8")

    total = sum(len(g["features"]) for g in datasets.values())
    print(f"wrote {output} ({len(datasets)}データ / {total}件)")


if __name__ == "__main__":
    main()
