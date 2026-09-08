import streamlit as st
from plateaukit import load_dataset
import pydeck as pdk

from analysis.colors import scale_color, usage_color
from analysis.loader import list_csv_files, load_csv

target_folder = "activelist"
DATASET_ID = "plateau-13106-taito-ku-2024"

with st.sidebar:
    base_data_name=st.selectbox('対象のデータ', list_csv_files(target_folder))

dataframe=load_csv(target_folder, base_data_name)
# Apply the function to create a color column
dataframe['color'] = dataframe['坪単価'].apply(lambda x: scale_color(x))

# ユーザーが駅を選ぶ
station = st.selectbox("駅を選んでください", ["蔵前駅"])

# 都市データ読み込み（例: 台東区）
dataset = load_dataset(DATASET_ID)

# plateauのlayerの定義　対象エリアを取得
try:
    area = dataset.area_from_landmark(station, min_size=[3000, 3000])
    gdf = area.gdf.copy()
except RuntimeError:
    st.error(
        f"PLATEAUデータセット `{DATASET_ID}` がローカルに未インストールです。"
        f"次のコマンドで取得してください:\n\n"
        f"```\nuv run plateaukit install {DATASET_ID}\n```"
    )
    st.stop()

gdf["fill_color"] = gdf["usage"].map(usage_color)


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

# scrapデータの処理
data = dataframe.to_dict(orient='records')

layer = pdk.Layer(
    "ColumnLayer",
    data=data,
    get_position="[lons, lats]",
    radius=4,
    get_elevation=400,
    get_fill_color="color",
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
