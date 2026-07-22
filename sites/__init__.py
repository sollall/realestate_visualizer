from .base import BaseSite
from .mansionreview import MansionReviewSite
from .suumo import SuumoSite

# サイト名と対応するクラスのマッピング
SITE_CLASSES = {
    "mansionreview": MansionReviewSite,
    "suumo": SuumoSite,
}
