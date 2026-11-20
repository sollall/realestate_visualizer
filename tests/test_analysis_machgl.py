import json
import re

import numpy as np
import pandas as pd

from analysis.colors import USAGE_COLOR_MAP
from analysis.machgl import (
    DEMO_API_KEY,
    build_map_html,
    to_geojson,
    usage_color_expression,
)


def test_usage_color_expression_covers_all_usages():
    expression = usage_color_expression()

    assert expression[:2] == ["match", ["get", "usage"]]
    labels = expression[2:-1:2]
    assert set(labels) == {k for k in USAGE_COLOR_MAP if k is not None}
    assert expression[expression.index("住宅") + 1] == "#addfad"
    # 末尾は未知の用途向けのフォールバック色
    assert re.fullmatch(r"#[0-9a-f]{6}", expression[-1])


def test_to_geojson_skips_rows_without_coordinates_and_converts_nan():
    df = pd.DataFrame({
        "address": ["A", "B", "C"],
        "lons": [139.79, np.nan, 139.80],
        "lats": [35.70, 35.71, 35.72],
        "坪単価": [np.int64(400), np.int64(500), np.int64(600)],
        "階数": ["5階", "3階", np.nan],
    })

    geojson = to_geojson(df, ["address", "坪単価", "階数"])

    assert [f["properties"]["address"] for f in geojson["features"]] == ["A", "C"]
    assert geojson["features"][0]["geometry"]["coordinates"] == [139.79, 35.70]
    assert geojson["features"][1]["properties"]["階数"] is None
    # numpyの型が残っているとjson.dumpsできないので、素のintになっていること
    assert json.dumps(geojson)


def test_build_map_html_embeds_key_center_and_escapes_script_tags():
    geojson = to_geojson(
        pd.DataFrame({"address": ["</script><b>x"], "lons": [139.79], "lats": [35.70]}),
        ["address"],
    )

    html = build_map_html(geojson, (139.79, 35.70), api_key=DEMO_API_KEY, building_opacity=0.5)

    assert "geolonia-api-key=YOUR-API-KEY" in html
    assert '"center": [139.79, 35.7]' in html
    assert '"buildingOpacity": 0.5' in html
    # データ中の</script>で埋め込みスクリプトが途中で閉じないこと
    assert html.count("</script>") == 2
