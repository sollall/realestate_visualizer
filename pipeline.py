from abc import ABC, abstractmethod


class Pipeline(ABC):
    """extract/transformを行うパイプラインの基底クラス"""

    # streamlit側(pages/app_estate.py)の表示に必要なカラム
    REQUIRED_COLUMNS = ["address", "area", "age", "lons", "lats", "坪単価"]

    @abstractmethod
    def extract(self):
        raise NotImplementedError

    @abstractmethod
    def transform(self, data):
        raise NotImplementedError

    def validate(self, data):
        """transform後のdfがstreamlitで読み込める形になっているか検証する"""
        if data.empty:
            return False

        if not all(col in data.columns for col in self.REQUIRED_COLUMNS):
            return False

        if data[self.REQUIRED_COLUMNS].isnull().any().any():
            return False

        return True
