import extract.mansionreview as extract_mansionreview
import transform.mansionreview as transform_mansionreview

from .core.pipeline import Pipeline


class MansionReviewPipeline(Pipeline):
    """マンションレビューの物件データを取得・加工するパイプライン"""

    def extract(self):
        return extract_mansionreview.scrap_estate_data()

    def transform(self, data):
        return transform_mansionreview.transform(data)
