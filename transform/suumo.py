import os

from .geocode import get_lat_lon
from .llm_clean import normalize_building_names, rule_based_clean

def transform(data):

    data["坪単価"] = data["price"] / 10000 / data["area"] * 3.306

    # 広告文句を除いた建物名。LLMでの正規化はAPI料金がかかるため環境変数で明示的に有効化する
    if os.environ.get("REALESTATE_LLM_CLEAN") == "1":
        data["building_name"] = normalize_building_names(data["name"].values)
    else:
        data["building_name"] = [rule_based_clean(n) for n in data["name"].values]

    lons,lats=get_lat_lon(data["address"].values)
    data["lons"]=lons
    data["lats"]=lats

    return data
