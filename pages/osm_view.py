"""売り出し中の物件から周囲を一人称視点で眺めるページ。

周辺の建物・道路などはOpenStreetMap(Overpass API)からその場で取得する。
"""

import pandas as pd
import pydeck as pdk
import requests
import streamlit as st
import streamlit.components.v1 as components

from analysis.loader import list_csv_files, load_csv
from analysis.osm_view import (
    FLOOR_HEIGHT_M,
    bearing_from_direction,
    build_scene,
    eye_height,
    offset_lonlat,
    parse_floor,
    remove_buildings_at,
)
from analysis.view_html import build_view_html
from extract.osm import fetch_osm_features

target_folder = "activelist"

cached_load_csv = st.cache_data(load_csv)


# 同じ物件・同じ範囲を何度もOverpass APIに問い合わせないよう、取得結果を1日キャッシュする
@st.cache_data(ttl=60 * 60 * 24, show_spinner=False)
def cached_fetch_osm(lat, lon, radius_m):
    return fetch_osm_features(lat, lon, radius_m)


st.title("物件からの眺め")
st.caption(
    "売り出し中の物件の位置・階数から、周囲の建物(OpenStreetMap)を一人称視点で表示します。"
    " 地図データ © OpenStreetMap contributors"
)

with st.sidebar:
    base_data_name = st.selectbox("対象のデータ", list_csv_files(target_folder))

dataframe = cached_load_csv(target_folder, base_data_name)
dataframe = dataframe.dropna(subset=["lons", "lats"]).reset_index(drop=True)

if dataframe.empty:
    st.warning("座標(lons/lats)が付いている物件がありません。")
    st.stop()


def listing_label(row):
    parts = []
    if "name" in row and isinstance(row["name"], str):
        parts.append(row["name"])
    parts.append(str(row["address"]))
    if "階数" in row and pd.notna(row["階数"]):
        parts.append(str(row["階数"]))
    parts.append(f"{row['坪単価']:.0f}万円/坪")
    return " / ".join(parts)


with st.sidebar:
    selected_index = st.selectbox(
        "物件",
        dataframe.index,
        format_func=lambda i: listing_label(dataframe.loc[i]),
    )
    listing = dataframe.loc[selected_index]

    # 階数・向きの情報がある(mansionreviewなど)場合はそれを初期値にする
    default_floor = parse_floor(listing.get("階数")) or 1
    floor = st.number_input("階数", min_value=1, max_value=80, value=default_floor, step=1)
    default_bearing = bearing_from_direction(listing.get("向き"))
    bearing = st.slider("見る方角(北=0°, 時計回り)", 0, 359, int(default_bearing), step=5)
    pitch = st.slider("見上げ角(水平=0°)", -60, 60, -5, step=1)

    with st.expander("詳細設定"):
        radius_m = st.select_slider("周辺データの取得範囲[m]", [300, 500, 800, 1000, 1500], value=800)
        default_height = st.number_input(
            "高さ情報が無い建物の高さ[m]",
            min_value=3.0, max_value=60.0, value=FLOOR_HEIGHT_M * 2, step=1.0,
            help="OSMの建物は高さ(height)や階数(building:levels)のタグが無いものが多いため、その場合の高さです。",
        )
        hide_own_building = st.checkbox(
            "物件自身の建物を非表示", value=True,
            help="物件の位置を含む建物を描画すると、視点が壁の内側に入って何も見えなくなるため非表示にします。",
        )

lat, lon = float(listing["lats"]), float(listing["lons"])

try:
    with st.spinner("OpenStreetMapから周辺の建物を取得しています..."):
        osm_json = cached_fetch_osm(round(lat, 6), round(lon, 6), radius_m)
except requests.RequestException as e:
    st.error(f"Overpass APIからのデータ取得に失敗しました。時間をおいて再度お試しください。\n\n{e}")
    st.stop()

scene = build_scene(osm_json, default_height=default_height)
removed = []
if hide_own_building:
    scene, removed = remove_buildings_at(scene, lon, lat)

eye = eye_height(floor)

# 取得範囲より少し広めに地面を敷き、地平線付近が空にならないようにする
ground_size = radius_m * 3
ground_polygon = [
    list(offset_lonlat(*offset_lonlat(lon, lat, ground_size, 0), ground_size, 90)),
    list(offset_lonlat(*offset_lonlat(lon, lat, ground_size, 180), ground_size, 90)),
    list(offset_lonlat(*offset_lonlat(lon, lat, ground_size, 180), ground_size, 270)),
    list(offset_lonlat(*offset_lonlat(lon, lat, ground_size, 0), ground_size, 270)),
]

html = build_view_html(
    scene,
    lon=lon,
    lat=lat,
    eye_height=eye,
    bearing=bearing,
    pitch=pitch,
    ground_polygon=ground_polygon,
    title=f"{listing['address']} {floor}階",
)
components.html(html, height=620)

n_buildings = len(scene["buildings"])
n_tagged = sum(1 for b in scene["buildings"] if not b["estimated"])
col1, col2, col3 = st.columns(3)
col1.metric("周辺の建物数", n_buildings)
col2.metric("高さ情報ありの建物", f"{n_tagged} ({n_tagged / max(n_buildings, 1):.0%})")
col3.metric("目線の高さ", f"約{eye:.1f}m")
if n_buildings and n_tagged / n_buildings < 0.5:
    st.caption(
        "このエリアはOSM上で高さ情報が付いていない建物が多いため、灰色の建物は"
        f"一律{default_height:.0f}mとして描画しています(詳細設定で変更できます)。"
    )
if hide_own_building and not removed:
    st.caption("物件の位置を含む建物がOSM上に見つからなかったため、すべての建物を表示しています。")

# 位置関係の確認用に、真上から見た周辺地図と見ている方角を表示する
st.markdown("#### 周辺地図")
direction_end = offset_lonlat(lon, lat, radius_m * 0.6, bearing)
# pydeckの式では関数呼び出しが使えないため、高さに応じた色はPython側で計算しておく
overview_buildings = [
    {**b, "color": [120, 140, 170, int(30 + min(b["height"], 60) * 3)], "height_label": f"{b['height']:.0f}"}
    for b in scene["buildings"]
]
overview = pdk.Deck(
    layers=[
        pdk.Layer(
            "PolygonLayer",
            data=overview_buildings,
            get_polygon="polygon",
            get_fill_color="color",
            get_line_color=[80, 80, 80, 120],
            line_width_min_pixels=0.5,
            pickable=True,
        ),
        pdk.Layer(
            "LineLayer",
            data=[{"from": [lon, lat], "to": list(direction_end)}],
            get_source_position="from",
            get_target_position="to",
            get_color=[230, 60, 30],
            get_width=4,
        ),
        pdk.Layer(
            "ScatterplotLayer",
            data=[{"position": [lon, lat]}],
            get_position="position",
            get_fill_color=[230, 60, 30],
            get_radius=12,
            radius_min_pixels=6,
        ),
    ],
    initial_view_state=pdk.ViewState(latitude=lat, longitude=lon, zoom=15.5),
    map_style="light",
    tooltip={"text": "{name} 高さ: {height_label}m"},
)
st.pydeck_chart(overview)
