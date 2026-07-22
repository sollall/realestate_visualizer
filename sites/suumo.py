import extract.suumo as extract_suumo
import transform.suumo as transform_suumo

from .base import BaseSite


class SuumoSite(BaseSite):
    name = "suumo"

    def extract(self):
        return extract_suumo.get_estate_data()

    def transform(self, data):
        return transform_suumo.transform(data)
