import numpy as np
import pydeck as pdk
import streamlit as st

from analysis.bayes import fit_price_surface
from analysis.colors import scale_color
from analysis.loader import list_csv_files, load_csv

st.set_page_config(page_title="単価マップ(ベイズ推定)", layout="wide")
st.title("単価マップ(RBF基底のベイズ線形回帰)")

target_folder = "activelist"

with st.sidebar:
    base_data_name = st.selectbox("対象のデータ", list_csv_files(target_folder))
    grid_size = st.slider("グリッド解像度", min_value=20, max_value=100, value=50, step=5)

data = load_csv(target_folder, base_data_name)

extra_columns = []
slice_values = {}

with st.sidebar:
    st.subheader("断面(この値に固定して地図を作る)")

    age_min, age_max = float(data["age"].min()), float(data["age"].max())
    if age_max > age_min:
        age_slice = st.slider("築年数", age_min, age_max, float(data["age"].median()))
        extra_columns.append("age")
        slice_values["age"] = age_slice

    # 「7階」のような文字列から階数を数値として取り出す。取得できなかった行はNaNになる
    if "階数" in data.columns:
        data["floor_num"] = data["階数"].astype(str).str.extract(r"(-?\d+)").iloc[:, 0].astype(float)
        floor_values = data["floor_num"].dropna()
        if len(floor_values) >= 5 and floor_values.max() > floor_values.min():
            floor_slice = st.slider(
                "階数", float(floor_values.min()), float(floor_values.max()), float(floor_values.median())
            )
            extra_columns.append("floor_num")
            slice_values["floor_num"] = floor_slice

with st.spinner("ベイズ線形回帰を計算中..."):
    grid_df, model = fit_price_surface(
        data,
        grid_size=grid_size,
        extra_columns=tuple(extra_columns),
        slice_values=slice_values,
    )

if grid_df.empty:
    st.warning("この地点・断面に近い観測データが無いため、地図を描画できませんでした。グリッド解像度や断面の値を変えてみてください。")
    st.stop()

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
