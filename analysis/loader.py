"""pages側がanalytics用CSVを読み込むための共通処理。

extract/transform(pipelines)が`data/analytics/<folder>/`配下に書き出したCSVを
読むだけの薄い層。pagesはファイルパスの組み立てやpandasの読み込みオプションを
意識せずにここを経由する。
"""

import json
import os

import pandas as pd

ANALYTICS_ROOT = "data/analytics"
RAILWAY_ROOT = "data/rawdata/railway"


def list_csv_files(folder):
    """`data/analytics/<folder>/`配下のCSVファイル名一覧を返す。"""
    directory = os.path.join(ANALYTICS_ROOT, folder)
    return [f for f in os.listdir(directory) if f.endswith(".csv")]


def load_csv(folder, filename):
    """`data/analytics/<folder>/<filename>`を読み込む。"""
    path = os.path.join(ANALYTICS_ROOT, folder, filename)
    return pd.read_csv(path, index_col=0)


def load_railway_geojson():
    """`data/rawdata/railway/`配下のGeoJSONを路線用・駅用に分けて読み込む。

    scripts/fetch_railway_data.pyが保存するファイル名(...RailroadSection.geojson /
    ...Station.geojson)を元に分類する。ファイルがまだ無い場合はそれぞれNoneを返す。
    """
    lines_geojson = None
    stations_geojson = None

    if not os.path.isdir(RAILWAY_ROOT):
        return lines_geojson, stations_geojson

    for filename in os.listdir(RAILWAY_ROOT):
        if not filename.lower().endswith(".geojson"):
            continue

        with open(os.path.join(RAILWAY_ROOT, filename), encoding="utf-8") as f:
            data = json.load(f)

        if "station" in filename.lower():
            stations_geojson = data
        elif "railroadsection" in filename.lower():
            lines_geojson = data

    return lines_geojson, stations_geojson
