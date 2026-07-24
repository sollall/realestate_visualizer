from .extract import scrap_estate_data
from .transform import transform

from ..core.pipeline import Pipeline


class MansionReviewPipeline(Pipeline):
    """マンションレビューの物件データを取得・加工するパイプライン"""

    def extract(self):
        return scrap_estate_data()

    def transform(self, data):
        return transform(data)
