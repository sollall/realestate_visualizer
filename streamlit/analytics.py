# tut_6.py
import os
import pandas as pd
import streamlit as st
from st_aggrid import AgGrid
from st_aggrid.grid_options_builder import GridOptionsBuilder
#add
from st_aggrid.shared import GridUpdateMode

st.set_page_config(page_title="過去の取引履歴", layout="wide") 
st.title("analysis")

# 絞り込み条件の設定
# Sidebar for external website
with st.sidebar:
    target_folder=st.selectbox(
    '対象のデータを含むフォルダ',
    ['transactionhistory'])
    base_data_name=st.selectbox(
    '対象のデータ',
    [f for f in os.listdir("data/transactionhistory") if f.endswith(".csv")])

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

#販売終了年月が空白のでーたは表示しないようにするか切り替えられるボタンがほしい
hide_empty = st.checkbox("販売終了年月が空白のデータを表示しない", value=True)

shows = pd.read_csv(f"data/{target_folder}/{base_data_name}",index_col=0)
gb = GridOptionsBuilder.from_dataframe(shows)

# ---
shows=shows[(shows['専有面積']>=price_range[0]) & (shows['専有面積']<=price_range[1])]
# データのフィルタリング
if hide_empty:
    # NaNまたは空文字列を除く
    shows = shows[shows["販売終了年月"] != "ー"]
else:
    shows = shows


gb.configure_selection(selection_mode="multiple", use_checkbox=True)

gridOptions = gb.build()


data = AgGrid(shows, 
              gridOptions=gridOptions, 
              enable_enterprise_modules=True, 
              allow_unsafe_jscode=True, 
              update_mode=GridUpdateMode.SELECTION_CHANGED)

# st.write(data["selected_rows"])

# add
import plotly_express as px

selected_rows = data["selected_rows"]
selected_rows = pd.DataFrame(selected_rows)

if len(selected_rows) != 0:
    fig = px.bar(selected_rows, "rating", color="type")
    st.plotly_chart(fig)
