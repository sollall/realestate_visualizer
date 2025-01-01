import streamlit as st
import pydeck as pdk
import pandas as pd
import numpy as np

dataframe=pd.read_csv("suumo_loc.csv",index_col=0)

# Function to scale colors
def scale_color(value, min_value, max_value):
    # Normalize the value to be between 0 and 1
    normalized = (value - min_value) / (max_value - min_value)
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

# Apply the function to create a color column
dataframe["log_price"] = dataframe["price per unit area"].apply(lambda x: np.log(x))
min_value = dataframe['log_price'].min()
max_value = dataframe['log_price'].max()
dataframe['color'] = dataframe['log_price'].apply(lambda x: scale_color(x, min_value, max_value))

data = dataframe.to_dict(orient='records')

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
    map_style=None,
)

event = st.pydeck_chart(
    chart,
    selection_mode="single-object",
    on_select="rerun",
)


a=event.selection

print(a["indices"]["map"][0])

