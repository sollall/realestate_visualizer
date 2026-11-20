import os

import streamlit as st
import streamlit.components.v1 as components

from analysis.colors import scale_color, usage_legend
from analysis.loader import list_csv_files, load_csv
from analysis.machgl import DEMO_API_KEY, build_map_html, to_geojson

target_folder = "activelist"
MAP_HEIGHT = 720

# 東京23区: 区名 -> (表示の中心に使う代表駅, (経度, 緯度))
# 駅は既存のplateauページ(plateau.py)のWARD_DATASETSに合わせている。
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

# 独自ドメインで公開する場合は環境変数GEOLONIA_API_KEYに本番用のキーを設定する。
# 未設定ならlocalhostでのみ動くデモキーを使う。
api_key = os.environ.get("GEOLONIA_API_KEY", DEMO_API_KEY)

with st.sidebar:
    base_data_name = st.selectbox('対象のデータ', list_csv_files(target_folder))
    ward = st.selectbox("対象の区", list(WARD_CENTERS.keys()), index=list(WARD_CENTERS.keys()).index("台東区"))
    opacity = st.slider("建物の不透明度", 0.1, 1.0, 0.8, step=0.05)

station, center = WARD_CENTERS[ward]
st.caption(
    f"{ward}({station}周辺)を中心に、MachGL(Geolonia)でPLATEAUの3D建物を表示しています。"
    "地図はドラッグで移動、右ドラッグ/Ctrl+ドラッグで傾き・回転できます。物件のマーカー(坪単価で色分け)をクリックすると詳細が出ます。"
)
if api_key == DEMO_API_KEY:
    st.caption("GeoloniaのデモキーはlocalhostなどGeoloniaが許可した環境でのみ地図を表示できます。")

dataframe = load_csv(target_folder, base_data_name)
dataframe['color'] = dataframe['坪単価'].apply(lambda x: scale_color(x))
if '階数' not in dataframe.columns:
    dataframe['階数'] = None

geojson = to_geojson(dataframe, ["address", "坪単価", "階数", "color"])

with st.sidebar:
    st.markdown("**建物用途の凡例**")
    legend_html = ""
    current_group = None
    for group, label, color in usage_legend():
        if group != current_group:
            legend_html += f"<div style='margin-top:6px;font-weight:600;'>{group}</div>"
            current_group = group
        swatch = f"rgb({color[0]},{color[1]},{color[2]})"
        legend_html += (
            "<div style='display:flex;align-items:center;margin:2px 0;'>"
            f"<span style='display:inline-block;width:14px;height:14px;"
            f"background:{swatch};border-radius:2px;margin-right:6px;flex-shrink:0;'></span>"
            f"<span>{label}</span></div>"
        )
    st.markdown(legend_html, unsafe_allow_html=True)

components.html(
    build_map_html(geojson, center, api_key=api_key, building_opacity=opacity, height=MAP_HEIGHT),
    height=MAP_HEIGHT,
)
