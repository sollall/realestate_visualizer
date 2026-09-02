"""pages側がanalytics用CSVを読み込むための共通処理。

extract/transform(pipelines)が`data/analytics/<folder>/`配下に書き出したCSVを
読むだけの薄い層。pagesはファイルパスの組み立てやpandasの読み込みオプションを
意識せずにここを経由する。
"""

import os

import pandas as pd

ANALYTICS_ROOT = "data/analytics"


def list_csv_files(folder):
    """`data/analytics/<folder>/`配下のCSVファイル名一覧を返す。"""
    directory = os.path.join(ANALYTICS_ROOT, folder)
    return [f for f in os.listdir(directory) if f.endswith(".csv")]


def load_csv(folder, filename):
    """`data/analytics/<folder>/<filename>`を読み込む。"""
    path = os.path.join(ANALYTICS_ROOT, folder, filename)
    return pd.read_csv(path, index_col=0)
