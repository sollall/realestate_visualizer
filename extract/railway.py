"""国土数値情報(鉄道 N02)の路線・駅データを取得するIF層のユーティリティ。

MLIT(国土交通省)の国土数値情報ダウンロードサービスが配布する鉄道データ(N02)のzipには、
シェープファイル一式に加えてGeoJSON形式のファイルもそのまま同梱されているため、
シェープファイル用のライブラリ(geopandas等)を増やさずに取り出して使える。
"""

import io
import zipfile

from extract.utils import load_page

# 年度コードは配布ページ(https://nlftp.mlit.go.jp/ksj/gml/datalist/KsjTmplt-N02-<年>.html)
# に記載のzipファイル名(例: 令和5年度データならN02-23_GML.zip)の数字部分。
ZIP_URL_TEMPLATE = "https://nlftp.mlit.go.jp/ksj/gml/data/N02/N02-{year_code}/N02-{year_code}_GML.zip"


def fetch_railway_geojson(year_code):
    """指定年度の全国鉄道データ(zip)をダウンロードし、中身のGeoJSONファイルを
    {ファイル名: バイト列} の辞書で返す。

    zipには路線(RailroadSection)と駅(Station)のGeoJSONに加えてshapefileや
    メタデータXMLも同梱されているため、拡張子が.geojsonのものだけを取り出す。
    """
    url = ZIP_URL_TEMPLATE.format(year_code=year_code)
    response = load_page(url)
    response.raise_for_status()

    geojson_files = {}
    with zipfile.ZipFile(io.BytesIO(response.content)) as zf:
        for name in zf.namelist():
            if name.lower().endswith(".geojson"):
                geojson_files[name] = zf.read(name)
    return geojson_files
