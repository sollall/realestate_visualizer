"""MachGL(Geolonia)でPLATEAUの3D建物と物件を描画するHTMLを組み立てる処理。

MachGLはブラウザで動くJSライブラリなので、pages側はここで作ったHTMLを
streamlitのcomponents.htmlで埋め込むだけにしている。PLATEAUの建物は
Geolonia配信のスタイル(geolonia/toranomon)に全国分が含まれており、
plateaukitのようなローカルへのデータセットインストールは不要。
"""

import json
import math

from analysis.colors import USAGE_COLOR_MAP

MACHGL_SCRIPT_URL = "https://cdn.geolonia.com/machgl/main/?geolonia-api-key={api_key}"
# localhostやGitHub Pagesなど開発・プレビュー環境でのみ使えるGeoloniaのデモキー。
# 独自ドメインで公開する場合はダッシュボードで発行した本番用のキーが必要。
DEMO_API_KEY = "YOUR-API-KEY"
PLATEAU_STYLE = "geolonia/toranomon"
# geolonia/toranomonスタイル内のPLATEAU建物レイヤのid
BUILDING_LAYER_ID = "buildings"
DEFAULT_BUILDING_COLOR = (200, 200, 200)


def _hex(rgb):
    return "#{:02x}{:02x}{:02x}".format(*rgb[:3])


def usage_color_expression():
    """建物用途(usage属性)で色分けするMachGL(MapLibre互換)のmatch式を返す。"""
    expression = ["match", ["get", "usage"]]
    for label, color in USAGE_COLOR_MAP.items():
        if label is None:
            continue
        expression += [label, _hex(color)]
    expression.append(_hex(DEFAULT_BUILDING_COLOR))
    return expression


def _json_value(value):
    """GeoJSONのpropertiesに入れられる値に変換する(NaNはnullにする)。"""
    if isinstance(value, float) and math.isnan(value):
        return None
    if hasattr(value, "item"):  # numpyのスカラー
        return _json_value(value.item())
    return value


def to_geojson(dataframe, columns):
    """物件のDataFrame(lons/lats列)をPoint FeatureのFeatureCollectionに変換する。

    座標が欠けている行は地図に置けないので除外する。
    """
    features = []
    for record in dataframe.to_dict(orient="records"):
        lon, lat = _json_value(record.get("lons")), _json_value(record.get("lats"))
        if lon is None or lat is None:
            continue
        features.append({
            "type": "Feature",
            "geometry": {"type": "Point", "coordinates": [lon, lat]},
            "properties": {c: _json_value(record.get(c)) for c in columns},
        })
    return {"type": "FeatureCollection", "features": features}


def _script_json(value):
    # <script>内に埋め込むため、文字列中の"</script>"でタグが閉じないようにする
    return json.dumps(value, ensure_ascii=False).replace("</", "<\\/")


def build_map_html(geojson, center, api_key=DEMO_API_KEY, building_opacity=0.8,
                   zoom=16, pitch=60, bearing=0, height=720):
    """PLATEAUの建物(用途で色分け)と物件のマーカーを重ねた地図のHTMLを返す。

    物件のpropertiesには"color"([r, g, b, a])と、ポップアップ用の
    "address"/"坪単価"/"階数"を想定している。
    """
    options = {
        "center": list(center),
        "zoom": zoom,
        "pitch": pitch,
        "bearing": bearing,
        "style": PLATEAU_STYLE,
        "buildingLayer": BUILDING_LAYER_ID,
        "buildingColor": usage_color_expression(),
        "buildingOpacity": building_opacity,
    }
    script_url = MACHGL_SCRIPT_URL.format(api_key=api_key)
    return f"""<!doctype html>
<html><head><meta charset="utf-8">
<style>
  html, body {{ margin: 0; padding: 0; }}
  #map {{ width: 100%; height: {height}px; }}
  .estate-popup {{ font: 12px/1.5 sans-serif; }}
  .estate-marker {{
    width: 14px; height: 14px; border-radius: 50%; cursor: pointer;
    border: 2px solid #fff; box-shadow: 0 0 3px rgba(0, 0, 0, 0.6);
  }}
</style>
</head><body>
<div id="map"></div>
<script src="{script_url}"></script>
<script>
const options = {_script_json(options)};
const estates = {_script_json(geojson)};

const map = new geolonia.Map({{
  container: "map",
  style: options.style,
  center: options.center,
  zoom: options.zoom,
  pitch: options.pitch,
  bearing: options.bearing,
}});

map.on("load", () => {{
  if (map.getLayer(options.buildingLayer)) {{
    map.setPaintProperty(options.buildingLayer, "bld-color", options.buildingColor);
    map.setPaintProperty(options.buildingLayer, "bld-roof-color", options.buildingColor);
    map.setPaintProperty(options.buildingLayer, "bld-opacity", options.buildingOpacity);
  }}

}});

// 物件はHTMLマーカーで置く。WebGLのレイヤだと3D建物に隠れてしまうが、
// HTMLマーカーは地図の上に重なるので常に見える。
// スクレイピングしたデータをHTMLとして解釈させないよう、textContentで組み立てる
const fmt = (v) => (v === null || v === undefined ? "-" : String(v));
for (const feature of estates.features) {{
  const p = feature.properties;
  const [r, g, b] = p.color || [128, 128, 128];
  const dot = document.createElement("div");
  dot.className = "estate-marker";
  dot.style.background = `rgb(${{r}},${{g}},${{b}})`;

  const root = document.createElement("div");
  root.className = "estate-popup";
  const title = document.createElement("b");
  title.textContent = fmt(p.address);
  const detail = document.createElement("div");
  detail.textContent = `坪単価: ${{fmt(p["坪単価"])}}万円 / 階数: ${{fmt(p["階数"])}}`;
  root.append(title, detail);

  new geolonia.Marker({{ element: dot }})
    .setLngLat(feature.geometry.coordinates)
    .setPopup(new geolonia.Popup({{ offset: 10 }}).setDOMContent(root))
    .addTo(map);
}}
</script>
</body></html>
"""
