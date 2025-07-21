import streamlit as st
from plateaukit import load_dataset
import pydeck as pdk

# 都市データ読み込み（例: 渋谷区）
dataset = load_dataset("plateau-13113-shibuya-ku-2023")

# ユーザーが駅を選ぶ
station = st.selectbox("駅を選んでください", ["渋谷駅", "代々木駅", "恵比寿駅"])

# 対象エリアを取得
area = dataset.area_from_landmark(station)

gdf = area.gdf.copy()

bbox = gdf.total_bounds
points = [(bbox[0], bbox[1]), (bbox[2], bbox[3])]
# print(points)

view_state = pdk.data_utils.compute_view(points, view_proportion=1)
view_state.pitch = 45

opacity=1

deck = pdk.Deck(
    layers=[
        pdk.Layer(
            "GeoJsonLayer",
            data=gdf,
            filled=True,
            get_fill_color="fill_color || color || [255, 255, 255]",
            # get_fill_color=[255, 255, 255, 240],
            # get_line_color=[255, 255, 255],
            opacity=opacity,
            extruded=True,
            # wireframe=True,
            get_elevation="measuredHeight",
            #pickable=True,
            auto_highlight=True,
        )
        # pydeck.Layer(
        #     "PolygonLayer",
        #     data=self.gdf,
        #     get_polygon="geometry.coordinates",
        #     filled=True,
        #     stroked=False,
        #     get_fill_color=[0, 0, 0, 20],
        #     get_line_color=[0, 0, 0, 20],
        # )
    ],
    initial_view_state=view_state,
    # initial_view_state=pydeck.ViewState(
    #     latitude=cy,
    #     longitude=cx,
    #     zoom=1,
    #     pitch=0,
    #     bearing=0,
    # ),
    tooltip={
        "style": {
            "font-family": "sans-serif",
            "font-size": "8px",
            "color": "white",
        },
    },
)

st.pydeck_chart(deck)
