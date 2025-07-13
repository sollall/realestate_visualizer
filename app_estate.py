import streamlit as st
import pydeck as pdk
import pandas as pd
import os

from utils import sigmoid,get_diff_records

# Function to scale colors
def scale_color(value, gain=0.01, offset=-400):
    # Normalize the value to be between 0 and 1
    normalized=sigmoid(value,gain=gain,offset_x=offset)
    # Define a 7-color scale (e.g., from blue to red)
    colors = [
        [0, 0, 255, 160],   # Blue
        [0, 128, 255, 160], # Light Blue
        [0, 255, 255, 160], # Cyan
        [255, 255, 0, 160], # Yellow
        [255, 165, 0, 160], # Orange
        [255, 69, 0, 160],  # Orange Red
        [255, 0, 0, 160]    # Red
    ]
    # Map the normalized value to the corresponding color
    index = int(normalized * (len(colors) - 1))
    return colors[index]

# 対象のdataframeの選択
# 絞り込み条件の設定
# Sidebar for external website
with st.sidebar:
    target_folder=st.selectbox(
    '対象のデータを含むフォルダ',
    ['mansionreview', 'suumo'])
    base_data_name=st.selectbox(
    '対象のデータ',
    os.listdir(target_folder)[1:][::-1])

    diff_data_name=st.selectbox(
    '対象からの差分をとりたいデータ',
    [None]+os.listdir(target_folder)[1:][::-1])

    min_area = 0.0
    max_area = 150.0
    price_range = st.slider(
        '面積の指定',
        min_area, max_area, (min_area, max_area),
        step=1.0
    )

    min_age_years = 0.0
    max_age_years = 60.0
    age_years_range = st.slider(
        '築年数の指定',
        min_age_years, max_age_years, (min_age_years, max_age_years),
        step=1.0
    )

#flag
diff_mode=True if diff_data_name else False

#データの読み込み
if diff_mode:
    today=pd.read_csv(f"{target_folder}/{base_data_name}",index_col=0)
    yesterday=pd.read_csv(f"{target_folder}/{diff_data_name}",index_col=0)
    dataframe,_=get_diff_records(today,yesterday)
else:
    dataframe=pd.read_csv(f"{target_folder}/{base_data_name}",index_col=0)

# Apply the function to create a color column
dataframe['color'] = dataframe['坪単価'].apply(lambda x: scale_color(x))

#条件に合わせたデータ絞り込み
#セッションステートにしているのは逐次追加したかった時の名残
dataframe=dataframe[(dataframe['面積']>=price_range[0]) & (dataframe['面積']<=price_range[1])]
dataframe=dataframe[(dataframe['築年数']>=age_years_range[0]) & (dataframe['築年数']<=age_years_range[1])]
data = dataframe.to_dict(orient='records')
st.session_state.candidates=pd.DataFrame(columns=dataframe.columns)

## 地図部分の作成
# レイヤーを設定
layer = pdk.Layer(
    "ScatterplotLayer",
    data=data,
    get_position="[lons, lats]",
    get_color="color",
    get_radius=100 if diff_mode else 30,
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
    map_style="mapbox://styles/mapbox/streets-v11",
)

event = st.pydeck_chart(
    chart,
    selection_mode="single-object",
    on_select="rerun",
)

selected=event.selection

if "map" in selected["indices"]:
    selected_index=selected["indices"]["map"][0]
    selected_address=dataframe.iloc[selected_index]["住所"]
    st.session_state.candidates=pd.concat([st.session_state.candidates, dataframe[dataframe["住所"]==selected_address]])
    st.dataframe(st.session_state.candidates)


st.markdown("### External Website")
st.markdown(
    """
    <iframe src="https://www.example.com" width="100%" height="500"></iframe>
    """,
    unsafe_allow_html=True
)