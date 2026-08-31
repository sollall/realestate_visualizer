from abc import ABC, abstractmethod

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
        """extract直後の生データが最低限の形になっているか検証する"""
        return all(col in data for col in RAW_REQUIRED_COLUMNS)

    def validate(self, data):
        """transform後のdfがanalysis.schemaの要件を満たしているか検証する"""
        if data.empty:
            return False

        if not all(col in data.columns for col in REQUIRED_COLUMNS):
            return False

        if data[REQUIRED_COLUMNS].isnull().any().any():
            return False

        return True
