import streamlit as st
import pandas as pd
import pydeck as pdk
import numpy as np
from cmcrameri import cm

# 元のデータフレームに追加します
data=pd.read_csv("suumo_20250714.csv",index_col=0)

colors = cm.hawaii_r(np.linspace(0, 1, 256))
rgb_colors = (colors[:, :3] * 255).astype(int).tolist()

data["log"]=data["price per unit area"].apply(lambda x: np.log10(x))
min_height = data["log"].min()
max_height = data["log"].max()
data["color"] = data["log"].apply(
    lambda h: rgb_colors[int(255 * ((h - min_height) / (max_height - min_height)))]
)

# 都心3区のリスト
exclude_wards = ["千代田区", "中央区", "港区", "新宿区", "文京区", "渋谷区"]
# 都心3区のレコードを除外
data = data[~data["address"].str.contains('|'.join(exclude_wards))]

data["view"]=data["price per unit area"]

# PyDeckを使用して地図を描画します
st.pydeck_chart(pdk.Deck(
    map_style=None,
    initial_view_state=pdk.ViewState(
        latitude=35.6802117,
        longitude=139.7576692,
        zoom=12,
        pitch=50,
    ),
    layers=[
        pdk.Layer(
            'ColumnLayer',
            data=data,
            get_position=['lons', 'lats'],
            get_elevation='view',
            elevation_scale=.001,
            radius=50,
            get_fill_color="color",
            pickable=True,
            extruded=True,
        ),
    ],
))
