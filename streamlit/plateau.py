import streamlit as st
from plateaukit import load_dataset
import pydeck as pdk
import pandas as pd
from geopandas import GeoDataFrame
import requests

# 都市データ読み込み（例: 渋谷区）
dataset = load_dataset("plateau-13113-shibuya-ku-2023")
dataframe=pd.read_csv("data/activelist/mansionreview_20250714.csv",index_col=0)

# ユーザーが駅を選ぶ
station = st.selectbox("駅を選んでください", ["渋谷駅", "代々木駅", "恵比寿駅"])

# plateauのlayerの定義　対象エリアを取得
area = dataset.area_from_landmark(station)
gdf = area.gdf.copy()
usage_color_map = {
    "住宅": [135, 206, 250],         # 水色
    "共同住宅": [70, 130, 180],      # 鉄紺
    "店舗等併用住宅": [102, 205, 170],  # 青緑
    "商業施設": [255, 140, 0],        # 橙
    "業務施設": [255, 215, 0],        # 金色
    "宿泊施設": [255, 105, 180],      # ピンク
    "文教厚生施設": [138, 43, 226],     # 青紫
    "官公庁施設": [255, 0, 0],         # 赤
    "運輸倉庫施設": [128, 128, 128],    # グレー
    "供給処理施設": [0, 128, 0],        # 緑
    "作業所併用住宅": [0, 206, 209],    # 青緑
    None: [200, 200, 200]             # 未設定は薄グレー
}
gdf["fill_color"] = gdf["usage"].map(lambda u: usage_color_map.get(u, [200, 200, 200]))


bbox = gdf.total_bounds
points = [(bbox[0], bbox[1]), (bbox[2], bbox[3])]
view_state = pdk.data_utils.compute_view(points, view_proportion=1)
view_state.pitch = 45
opacity = 1

# 建物の3D表示レイヤー（tooltipに使える列を追加）
#gdf["name"] = gdf.index.astype(str)  # tooltipに使う列

building3d = pdk.Layer(
    "GeoJsonLayer",
    data=gdf,
    filled=True,
    get_fill_color="fill_color",
    opacity=opacity,
    extruded=True,
    get_elevation="measuredHeight",
    pickable=True,  # ← 有効化
    auto_highlight=True,
)

# 港区AEDのデータ取得
MINATO_AED_GEOJSON_URL = "https://opendata.city.minato.tokyo.jp/dataset/a67952bc-b318-4ab4-a797-187607c4ecf4/resource/3ccd1270-9ea7-481b-a97a-19ca80d22d05/download/minato_aed.json"
data = requests.get(MINATO_AED_GEOJSON_URL)
minato_aed_gdf = GeoDataFrame.from_features(data.json())

# tooltip用に "name" 列を追加
minato_aed_gdf["name"] = "AED"

layer = pdk.Layer(
    "ColumnLayer",
    data=minato_aed_gdf,
    get_position="geometry.coordinates",
    radius=4,
    get_elevation=400,
    get_fill_color=[255, 0, 0],
    pickable=True,  # ← 有効化
    auto_highlight=True,
)

# デッキの作成
deck = pdk.Deck(
    layers=[
        layer,
        building3d,
    ],
    initial_view_state=view_state,
    tooltip={
        "html": "<b>{name}</b>",
        "style": {
            "font-family": "sans-serif",
            "font-size": "10px",
            "color": "white",
        },
    },
)

st.pydeck_chart(deck)
