import extract.mansionreview as extract_mansionreview
import transform.mansionreview as transform_mansionreview

from .base import BaseSite


class MansionReviewSite(BaseSite):
    name = "mansionreview"

    def extract(self):
        return extract_mansionreview.scrap_estate_data()

    def transform(self, data):
        return transform_mansionreview.transform(data)
