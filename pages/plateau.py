import streamlit as st
from plateaukit import load_dataset
import pydeck as pdk

from analysis.colors import scale_color, usage_color, usage_legend
from analysis.loader import list_csv_files, load_csv

target_folder = "activelist"

# 東京23区: 区名 -> (PLATEAUデータセットID, 表示の中心に使う代表駅)
WARD_DATASETS = {
    "千代田区": ("plateau-13101-chiyoda-ku-2023", "東京駅"),
    "中央区": ("plateau-13102-chuo-ku-2023", "銀座駅"),
    "港区": ("plateau-13103-minato-ku-2023", "六本木駅"),
    "新宿区": ("plateau-13104-shinjuku-ku-2023", "新宿駅"),
    "文京区": ("plateau-13105-bunkyo-ku-2023", "後楽園駅"),
    "台東区": ("plateau-13106-taito-ku-2024", "蔵前駅"),
    "墨田区": ("plateau-13107-sumida-ku-2024", "錦糸町駅"),
    "江東区": ("plateau-13108-koto-ku-2023", "豊洲駅"),
    "品川区": ("plateau-13109-shinagawa-ku-2024", "品川駅"),
    "目黒区": ("plateau-13110-meguro-ku-2023", "目黒駅"),
    "大田区": ("plateau-13111-ota-ku-2023", "蒲田駅"),
    "世田谷区": ("plateau-13112-setagaya-ku-2023", "三軒茶屋駅"),
    "渋谷区": ("plateau-13113-shibuya-ku-2023", "渋谷駅"),
    "中野区": ("plateau-13114-nakano-ku-2023", "中野駅"),
    "杉並区": ("plateau-13115-suginami-ku-2024", "荻窪駅"),
    "豊島区": ("plateau-13116-toshima-ku-2023", "池袋駅"),
    "北区": ("plateau-13117-kita-ku-2023", "赤羽駅"),
    "荒川区": ("plateau-13118-arakawa-ku-2023", "日暮里駅"),
    "板橋区": ("plateau-13119-itabashi-ku-2023", "板橋駅"),
    "練馬区": ("plateau-13120-nerima-ku-2023", "練馬駅"),
    "足立区": ("plateau-13121-adachi-ku-2023", "北千住駅"),
    "葛飾区": ("plateau-13122-katsushika-ku-2023", "亀有駅"),
    "江戸川区": ("plateau-13123-edogawa-ku-2023", "葛西駅"),
}

with st.sidebar:
    base_data_name=st.selectbox('対象のデータ', list_csv_files(target_folder))
    ward = st.selectbox("対象の区", list(WARD_DATASETS.keys()), index=list(WARD_DATASETS.keys()).index("台東区"))

dataframe=load_csv(target_folder, base_data_name)
# Apply the function to create a color column
dataframe['color'] = dataframe['坪単価'].apply(lambda x: scale_color(x))

DATASET_ID, station = WARD_DATASETS[ward]
st.caption(f"{ward}({station}周辺)のPLATEAUデータを表示しています。")

# 都市データ読み込み
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

with st.sidebar:
    st.markdown("**建物用途の凡例**")
    legend_html = ""
    current_group = None
    for group, label, color in usage_legend():
        if group != current_group:
            legend_html += f"<div style='margin-top:6px;font-weight:600;'>{group}</div>"
            current_group = group
        swatch = f"rgb({color[0]},{color[1]},{color[2]})"
        legend_html += (
            "<div style='display:flex;align-items:center;margin:2px 0;'>"
            f"<span style='display:inline-block;width:14px;height:14px;"
            f"background:{swatch};border-radius:2px;margin-right:6px;flex-shrink:0;'></span>"
            f"<span>{label}</span></div>"
        )
    st.markdown(legend_html, unsafe_allow_html=True)


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
