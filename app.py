import streamlit as st
import pydeck as pdk

# データを用意
data = [
    {"latitude": 35.6895, "longitude": 139.6917, "place": "東京"},
    {"latitude": 34.6937, "longitude": 135.5023, "place": "大阪"},
    {"latitude": 43.0642, "longitude": 141.3469, "place": "札幌"},
    {"latitude": 35.0116, "longitude": 135.7681, "place": "京都"},
    {"latitude": 33.5904, "longitude": 130.4017, "place": "福岡"},
]

# レイヤーを設定
layer = pdk.Layer(
    "ScatterplotLayer",
    data=data,
    get_position="[longitude, latitude]",
    get_color="[200, 30, 0, 160]",
    get_radius=50000,
    pickable=True,
    auto_highlight=True,
    id="map",
)

# 初期表示の設定
view_state = pdk.ViewState(
    latitude=36.2048,
    longitude=138.2529,
    zoom=3,
)

# Pydeckチャートを表示
chart = pdk.Deck(
    layers=[layer],
    initial_view_state=view_state,
    map_style=None,
)

event = st.pydeck_chart(
    chart,
    selection_mode="single-object",
    on_select="rerun",
)


a=event.selection

print(a["indices"]["map"][0])

