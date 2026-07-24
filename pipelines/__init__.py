from .suumo import SuumoPipeline
from .mansionreview import MansionReviewPipeline

# サイト名と対応するPipelineクラスのマッピング
PIPELINES = {
    "suumo": SuumoPipeline,
    "mansionreview": MansionReviewPipeline,
}
