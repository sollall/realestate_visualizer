import extract.suumo as extract_suumo
import transform.suumo as transform_suumo

from .core.pipeline import Pipeline


class SuumoPipeline(Pipeline):
    """SUUMOの物件データを取得・加工するパイプライン"""

    def extract(self):
        return extract_suumo.get_estate_data()

    def transform(self, data):
        return transform_suumo.transform(data)
