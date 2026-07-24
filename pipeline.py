from abc import ABC, abstractmethod

import extract.mansionreview as extract_mansionreview
import extract.suumo as extract_suumo
import transform.mansionreview as transform_mansionreview
import transform.suumo as transform_suumo


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


class SuumoPipeline(Pipeline):
    """SUUMOのextract/transformを行うパイプライン"""

    def extract(self):
        return extract_suumo.get_estate_data()

    def transform(self, data):
        return transform_suumo.transform(data)


class MansionReviewPipeline(Pipeline):
    """マンションレビューのextract/transformを行うパイプライン"""

    def extract(self):
        return extract_mansionreview.scrap_estate_data()

    def transform(self, data):
        return transform_mansionreview.transform(data)


PIPELINES = {
    "suumo": SuumoPipeline,
    "mansionreview": MansionReviewPipeline,
}
