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
bbox = gdf.total_bounds
points = [(bbox[0], bbox[1]), (bbox[2], bbox[3])]
view_state = pdk.data_utils.compute_view(points, view_proportion=1)
view_state.pitch = 45
opacity = 1

# 建物の3D表示レイヤー（tooltipに使える列を追加）
gdf["name"] = gdf.index.astype(str)  # tooltipに使う列

building3d = pdk.Layer(
    "GeoJsonLayer",
    data=gdf,
    filled=True,
    get_fill_color="fill_color || color || [255, 255, 255]",
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
