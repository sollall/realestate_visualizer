from abc import ABC, abstractmethod

import pandas as pd

from analysis.schema import REQUIRED_COLUMNS

# extract直後の生データに最低限必要なカラム(サイトによらず共通)
RAW_REQUIRED_COLUMNS = ["name", "price", "address", "area", "age"]


class Pipeline(ABC):
    """extract/transformを行うパイプラインの基底クラス。

    IF(extract)と生データ加工(transform)を1サイト単位でまとめる役割のみを持ち、
    可視化・分析側(analysis, pages)の実装には関与しない。
    可視化側が要求するデータ契約はanalysis.schemaを参照する。
    """

    @abstractmethod
    def extract(self):
        raise NotImplementedError

    @abstractmethod
    def transform(self, data):
        raise NotImplementedError

    def validate_raw(self, data):
        """extract直後の生データが最低限の形になっているか検証する

        カラムが揃っているかだけでなく、スクレイピング先のHTML構造の変化などで
        0件になっていないか・必須カラムがnull埋めされていないかも確認する。
        これによりextractが「エラーは出ないが中身が壊れている」状態を検知できる。
        """
        if not all(col in data for col in RAW_REQUIRED_COLUMNS):
            return False

        if isinstance(data, pd.DataFrame):
            if data.empty:
                return False

            if data[RAW_REQUIRED_COLUMNS].isnull().any().any():
                return False

        return True

    def validate(self, data):
        """transform後のdfがanalysis.schemaの要件を満たしているか検証する"""
        if data.empty:
            return False

        if not all(col in data.columns for col in REQUIRED_COLUMNS):
            return False

        if data[REQUIRED_COLUMNS].isnull().any().any():
            return False

        return True
