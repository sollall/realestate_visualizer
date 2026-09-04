import numpy as np
import pydeck as pdk
import streamlit as st

from analysis.bayes import fit_price_surface
from analysis.colors import scale_color
from analysis.loader import list_csv_files, load_csv

st.set_page_config(page_title="単価マップ(ベイズ推定)", layout="wide")
st.title("単価マップ(ガウス過程によるベイズ推定)")

target_folder = "activelist"

with st.sidebar:
    base_data_name = st.selectbox("対象のデータ", list_csv_files(target_folder))
    grid_size = st.slider("グリッド解像度", min_value=15, max_value=60, value=30, step=5)

data = load_csv(target_folder, base_data_name)

with st.spinner("ガウス過程回帰を計算中..."):
    grid_df, model = fit_price_surface(data, grid_size=grid_size)

# 不確実性(予測標準偏差)が大きいセルほど薄く表示する
std_min, std_max = grid_df["price_std"].min(), grid_df["price_std"].max()
confidence = 1 - (grid_df["price_std"] - std_min) / (std_max - std_min + 1e-9)
grid_df["color"] = [
    rgba[:3] + [int(30 + 170 * c)]
    for rgba, c in zip(grid_df["price_mean"].apply(scale_color), confidence)
]

# セル間隔(度)からおおよそのメートル換算でColumnLayerの半径を決める
mean_lat_rad = np.radians(data["lats"].mean())
lat_spacing_m = (grid_df["lats"].max() - grid_df["lats"].min()) / (grid_size - 1) * 111_000
lon_spacing_m = (grid_df["lons"].max() - grid_df["lons"].min()) / (grid_size - 1) * 111_000 * np.cos(mean_lat_rad)
radius = min(lat_spacing_m, lon_spacing_m) / 2

col1, col2 = st.columns(2)
with col1:
    st.metric("坪単価 推定の中央値", f"{grid_df['price_mean'].median():,.0f} 万円")
with col2:
    st.metric("観測データ件数", len(data))

layer = pdk.Layer(
    "ColumnLayer",
    data=grid_df,
    get_position="[lons, lats]",
    get_elevation="price_mean",
    elevation_scale=0.001,
    radius=radius,
    get_fill_color="color",
    pickable=True,
    auto_highlight=True,
)

view_state = pdk.data_utils.compute_view(grid_df[["lons", "lats"]].values.tolist())
view_state.pitch = 45

st.pydeck_chart(pdk.Deck(
    layers=[layer],
    initial_view_state=view_state,
    tooltip={"html": "<b>推定坪単価:</b> {price_mean}<br/><b>不確実性(標準偏差):</b> {price_std}"},
))
