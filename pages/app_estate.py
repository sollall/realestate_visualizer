import streamlit as st
import pydeck as pdk
import pandas as pd
import numpy as np

from analysis.colors import scale_color
from analysis.filters import filter_range
from analysis.loader import list_csv_files, load_csv, load_railway_geojson

target_folder = "activelist"

# 絞り込み条件の設定
# Sidebar for external website
with st.sidebar:
    base_data_name=st.selectbox(
    '対象のデータ',
    list_csv_files(target_folder))

    mapstyle=st.selectbox(
    '地図のスタイル',
    [
        'road',
        'dark',
        'light',
        'dark_no_labels',
        'light_no_labels',
    ])

    railway_lines_geojson, railway_stations_geojson = load_railway_geojson()
    if railway_lines_geojson is None and railway_stations_geojson is None:
        st.caption("鉄道データが見つかりません。`scripts/fetch_railway_data.py`を実行してください。")
        show_railway = False
    else:
        show_railway = st.checkbox('路線・駅を表示', value=True)

dataframe=load_csv(target_folder, base_data_name)

# Apply the function to create a color column
dataframe['color'] = dataframe['坪単価'].apply(lambda x: scale_color(x))

with st.sidebar:
    min_area = float(dataframe['area'].min())
    max_area = min(150.0,float(dataframe['area'].max()))
    price_range = st.slider(
        '面積の指定',
        min_area, max_area, (min_area, max_area),
        step=1.0
    )

    # サイトによってageの型(int/float)が異なるため明示的にfloat化する
    min_age_years = max(0.0,float(dataframe['age'].min()))
    max_age_years = min(60.0,float(dataframe['age'].max()))
    age_years_range = st.slider(
        '築年数の指定',
        min_age_years, max_age_years, (min_age_years, max_age_years),
        step=1.0
    )

#条件に合わせたデータ絞り込み
#セッションステートにしているのは逐次追加したかった時の名残
dataframe=filter_range(dataframe, 'area', price_range)
dataframe=filter_range(dataframe, 'age', age_years_range)
data = dataframe.to_dict(orient='records')
st.session_state.candidates=pd.DataFrame(columns=dataframe.columns)

## 地図部分の作成
# レイヤーを設定
layer = pdk.Layer(
    "ScatterplotLayer",
    data=data,
    get_position="[lons, lats]",
    get_color="color",
    get_radius=30,
    pickable=True,
    auto_highlight=True,
    id="map",
)

# 物件のマーカーが路線・駅の下に隠れないよう、路線・駅は先に(下に)積む
layers = []

if show_railway:
    if railway_lines_geojson is not None:
        layers.append(pdk.Layer(
            "GeoJsonLayer",
            data=railway_lines_geojson,
            stroked=True,
            filled=False,
            get_line_color=[120, 120, 120],
            line_width_min_pixels=1.5,
        ))
    if railway_stations_geojson is not None:
        layers.append(pdk.Layer(
            "GeoJsonLayer",
            data=railway_stations_geojson,
            stroked=True,
            filled=True,
            get_fill_color=[255, 255, 255, 220],
            get_line_color=[120, 120, 120],
            get_point_radius=40,
            point_radius_min_pixels=2,
        ))

layers.append(layer)

# 初期表示の設定
view_state = pdk.ViewState(
    latitude=35.6802117,
    longitude=139.7576692,
    zoom=12,
)

# Pydeckチャートを表示
chart = pdk.Deck(
    layers=layers,
    initial_view_state=view_state,
    map_style=mapstyle,
)

event = st.pydeck_chart(
    chart,
    selection_mode="single-object",
    on_select="rerun",
)

selected=event.selection

if "map" in selected["indices"]:
    selected_index=selected["indices"]["map"][0]
    selected_address=dataframe.iloc[selected_index]["address"]
    st.session_state.candidates=pd.concat([st.session_state.candidates, dataframe[dataframe["address"]==selected_address]])
    st.dataframe(st.session_state.candidates)


st.markdown("### External Website")
st.markdown(
    """
    <iframe src="https://www.example.com" width="100%" height="500"></iframe>
    """,
    unsafe_allow_html=True
)