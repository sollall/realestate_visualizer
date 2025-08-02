import streamlit as st
import pydeck as pdk
import pandas as pd
import numpy as np

from utils import scale_color

dataframe=pd.read_csv("data/analytics/activelist/mansionreview_20250727.csv",index_col=0)

# Apply the function to create a color column
dataframe['color'] = dataframe['坪単価'].apply(lambda x: scale_color(x))

# 絞り込み条件の設定
# Sidebar for external website
with st.sidebar:
    mapstyle=st.selectbox(
    '地図のスタイル',
    [
        'streets-v11',
        'dark-v11',
        'satellite-v9',
        'navigation-night-v1',
    ])

    min_area = dataframe['area'].min()
    max_area = min(150.0,dataframe['area'].max())
    price_range = st.slider(
        '面積の指定',
        min_area, max_area, (min_area, max_area),
        step=1.0
    )

    min_age_years = max(0.0,dataframe['age'].min())
    max_age_years = min(60.0,dataframe['age'].max())
    age_years_range = st.slider(
        '築年数の指定',
        min_age_years, max_age_years, (min_age_years, max_age_years),
        step=1.0
    )

#条件に合わせたデータ絞り込み
#セッションステートにしているのは逐次追加したかった時の名残
dataframe=dataframe[(dataframe['area']>=price_range[0]) & (dataframe['area']<=price_range[1])]
dataframe=dataframe[(dataframe['age']>=age_years_range[0]) & (dataframe['age']<=age_years_range[1])]
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

# 初期表示の設定
view_state = pdk.ViewState(
    latitude=35.6802117,
    longitude=139.7576692,
    zoom=12,
)

# Pydeckチャートを表示
chart = pdk.Deck(
    layers=[layer],
    initial_view_state=view_state,
    map_style=f"mapbox://styles/mapbox/{mapstyle}" ,
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