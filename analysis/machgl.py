"""MachGL(Geolonia)でPLATEAUの3D建物と物件を描画する単体HTMLを組み立てる処理。

MachGLはブラウザで動くJSライブラリなので、streamlitを介さずにHTMLファイルへ
物件データごと書き出し、データ・区の切り替えや建物の不透明度もページ内のJSで行う。
こうすると操作のたびに地図やPLATEAUのタイルを読み込み直さずに済む。
PLATEAUの建物はGeolonia配信のスタイル(geolonia/toranomon)に全国分が含まれており、
plateaukitのようなローカルへのデータセットインストールは不要。
"""

import json
import math

from analysis.colors import USAGE_COLOR_MAP, usage_legend

MACHGL_SCRIPT_URL = "https://cdn.geolonia.com/machgl/main/?geolonia-api-key={api_key}"
# localhostやGitHub Pagesなど開発・プレビュー環境でのみ使えるGeoloniaのデモキー。
# 独自ドメインで公開する場合はダッシュボードで発行した本番用のキーが必要。
DEMO_API_KEY = "YOUR-API-KEY"
PLATEAU_STYLE = "geolonia/toranomon"
# geolonia/toranomonスタイル内のPLATEAU建物レイヤのid
BUILDING_LAYER_ID = "buildings"
DEFAULT_BUILDING_COLOR = (200, 200, 200)

# 東京23区: 区名 -> (表示の中心に使う代表駅, (経度, 緯度))
# 駅はplateauページ(pages/plateau.py)のWARD_DATASETSに合わせている。
WARD_CENTERS = {
    "千代田区": ("東京駅", (139.7671, 35.6812)),
    "中央区": ("銀座駅", (139.7650, 35.6717)),
    "港区": ("六本木駅", (139.7314, 35.6628)),
    "新宿区": ("新宿駅", (139.7006, 35.6896)),
    "文京区": ("後楽園駅", (139.7517, 35.7077)),
    "台東区": ("蔵前駅", (139.7915, 35.7036)),
    "墨田区": ("錦糸町駅", (139.8140, 35.6966)),
    "江東区": ("豊洲駅", (139.7963, 35.6549)),
    "品川区": ("品川駅", (139.7388, 35.6285)),
    "目黒区": ("目黒駅", (139.7158, 35.6340)),
    "大田区": ("蒲田駅", (139.7161, 35.5626)),
    "世田谷区": ("三軒茶屋駅", (139.6707, 35.6437)),
    "渋谷区": ("渋谷駅", (139.7016, 35.6580)),
    "中野区": ("中野駅", (139.6657, 35.7057)),
    "杉並区": ("荻窪駅", (139.6200, 35.7046)),
    "豊島区": ("池袋駅", (139.7109, 35.7295)),
    "北区": ("赤羽駅", (139.7209, 35.7778)),
    "荒川区": ("日暮里駅", (139.7710, 35.7278)),
    "板橋区": ("板橋駅", (139.7193, 35.7456)),
    "練馬区": ("練馬駅", (139.6542, 35.7377)),
    "足立区": ("北千住駅", (139.8049, 35.7497)),
    "葛飾区": ("亀有駅", (139.8476, 35.7662)),
    "江戸川区": ("葛西駅", (139.8727, 35.6636)),
}
DEFAULT_WARD = "台東区"


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


def build_map_html(datasets, api_key=DEMO_API_KEY, initial_ward=DEFAULT_WARD,
                   building_opacity=0.8, zoom=16, pitch=60):
    """PLATEAUの建物(用途で色分け)と物件のマーカーを重ねた単体HTMLを返す。

    datasetsは{データ名: to_geojsonの戻り値}。物件のpropertiesには
    "color"([r, g, b, a])と、ポップアップ用の"address"/"坪単価"/"階数"を想定している。
    データ・区の切り替えと建物の不透明度はページ内のパネルで変更できる。
    """
    options = {
        "zoom": zoom,
        "pitch": pitch,
        "style": PLATEAU_STYLE,
        "buildingLayer": BUILDING_LAYER_ID,
        "buildingColor": usage_color_expression(),
        "buildingOpacity": building_opacity,
        "wards": {name: {"station": station, "center": list(center)}
                  for name, (station, center) in WARD_CENTERS.items()},
        "initialWard": initial_ward,
        "legend": [[group, label, _hex(color)] for group, label, color in usage_legend()],
    }
    script_url = MACHGL_SCRIPT_URL.format(api_key=api_key)
    return f"""<!doctype html>
<html lang="ja"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>PLATEAU物件マップ</title>
<style>
  html, body {{ margin: 0; padding: 0; height: 100%; font: 13px/1.5 sans-serif; }}
  #map {{ position: absolute; inset: 0; }}
  #panel {{
    position: absolute; top: 10px; left: 10px; z-index: 1; width: 220px;
    max-height: calc(100% - 40px); overflow-y: auto; padding: 10px 12px;
    background: rgba(255, 255, 255, 0.92); border-radius: 6px;
    box-shadow: 0 1px 4px rgba(0, 0, 0, 0.3);
  }}
  #panel label {{ display: block; margin-top: 8px; font-weight: 600; }}
  #panel select, #panel input[type=range] {{ width: 100%; box-sizing: border-box; }}
  #panel .note {{ margin-top: 6px; color: #666; font-size: 11px; }}
  #panel summary {{ margin-top: 10px; font-weight: 600; cursor: pointer; }}
  .legend-group {{ margin-top: 6px; font-weight: 600; }}
  .legend-item {{ display: flex; align-items: center; margin: 2px 0; }}
  .legend-item span {{ width: 12px; height: 12px; margin-right: 6px; border-radius: 2px; flex-shrink: 0; }}
  .estate-popup {{ font: 12px/1.5 sans-serif; }}
  .estate-marker {{
    width: 14px; height: 14px; border-radius: 50%; cursor: pointer;
    border: 2px solid #fff; box-shadow: 0 0 3px rgba(0, 0, 0, 0.6);
  }}
</style>
</head><body>
<div id="map"></div>
<div id="panel">
  <label for="dataset">対象のデータ</label>
  <select id="dataset"></select>
  <div class="note" id="count"></div>
  <label for="ward">対象の区</label>
  <select id="ward"></select>
  <label for="opacity">建物の不透明度 <span id="opacity-value"></span></label>
  <input id="opacity" type="range" min="0.1" max="1" step="0.05">
  <div class="note">ドラッグで移動、右ドラッグ/Ctrl+ドラッグで傾き・回転。物件のマーカー(坪単価で色分け)をクリックすると詳細が出ます。</div>
  <details open><summary>建物用途の凡例</summary><div id="legend"></div></details>
</div>
<script src="{script_url}"></script>
<script>
const options = {_script_json(options)};
const datasets = {_script_json(datasets)};
const $ = (id) => document.getElementById(id);

// スクレイピングしたデータをHTMLとして解釈させないよう、要素はtextContentで組み立てる
const el = (tag, className, text) => {{
  const e = document.createElement(tag);
  if (className) e.className = className;
  if (text !== undefined) e.textContent = text;
  return e;
}};

for (const name of Object.keys(datasets)) $("dataset").append(new Option(name, name));
for (const [name, ward] of Object.entries(options.wards)) {{
  $("ward").append(new Option(`${{name}}(${{ward.station}})`, name));
}}
$("ward").value = options.initialWard;
$("opacity").value = options.buildingOpacity;
$("opacity-value").textContent = options.buildingOpacity;

let group = null;
for (const [g, label, color] of options.legend) {{
  if (g !== group) {{ $("legend").append(el("div", "legend-group", g)); group = g; }}
  const item = el("div", "legend-item");
  const swatch = el("span");
  swatch.style.background = color;
  item.append(swatch, document.createTextNode(label));
  $("legend").append(item);
}}

const map = new geolonia.Map({{
  container: "map",
  style: options.style,
  center: options.wards[options.initialWard].center,
  zoom: options.zoom,
  pitch: options.pitch,
}});

const setBuildingPaint = (name, value) => {{
  if (map.getLayer(options.buildingLayer)) map.setPaintProperty(options.buildingLayer, name, value);
}};
map.on("load", () => {{
  setBuildingPaint("bld-color", options.buildingColor);
  setBuildingPaint("bld-roof-color", options.buildingColor);
  setBuildingPaint("bld-opacity", options.buildingOpacity);
}});

// 物件はHTMLマーカーで置く。WebGLのレイヤだと3D建物に隠れてしまうが、
// HTMLマーカーは地図の上に重なるので常に見える。
const fmt = (v) => (v === null || v === undefined ? "-" : String(v));
let markers = [];
function showDataset(name) {{
  markers.forEach((m) => m.remove());
  const features = datasets[name] ? datasets[name].features : [];
  markers = features.map((feature) => {{
    const p = feature.properties;
    const [r, g, b] = p.color || [128, 128, 128];
    const dot = el("div", "estate-marker");
    dot.style.background = `rgb(${{r}},${{g}},${{b}})`;
    const popup = el("div", "estate-popup");
    popup.append(el("b", null, fmt(p.address)),
      el("div", null, `坪単価: ${{fmt(p["坪単価"])}}万円 / 階数: ${{fmt(p["階数"])}}`));
    return new geolonia.Marker({{ element: dot }})
      .setLngLat(feature.geometry.coordinates)
      .setPopup(new geolonia.Popup({{ offset: 10 }}).setDOMContent(popup))
      .addTo(map);
  }});
  $("count").textContent = `${{features.length}}件の物件`;
}}

$("dataset").addEventListener("change", (e) => showDataset(e.target.value));
$("ward").addEventListener("change", (e) => {{
  map.flyTo({{ center: options.wards[e.target.value].center, zoom: options.zoom, pitch: options.pitch }});
}});
$("opacity").addEventListener("input", (e) => {{
  const value = Number(e.target.value);
  $("opacity-value").textContent = value;
  setBuildingPaint("bld-opacity", value);
}});
showDataset($("dataset").value);
</script>
</body></html>
"""
