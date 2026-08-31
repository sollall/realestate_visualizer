"""サイト名からPipelineを引くレジストリ。load.py(CLI)から使う。"""

from .mansionreview import MansionReviewPipeline
from .suumo import SuumoPipeline

PIPELINES = {
    "suumo": SuumoPipeline,
    "mansionreview": MansionReviewPipeline,
}
