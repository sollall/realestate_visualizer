from extract.suumo import get_estate_data
from transform.suumo import transform

from .core.pipeline import Pipeline


class SuumoPipeline(Pipeline):
    """SUUMOの物件データを取得・加工するパイプライン"""

    def extract(self):
        return get_estate_data()

    def transform(self, data):
        return transform(data)
