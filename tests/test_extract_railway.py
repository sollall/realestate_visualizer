"""extract/railway.pyのfetch_railway_geojson()が、zip内からGeoJSONファイルだけを
正しく取り出せることを確認するテスト。実際の外部(国土数値情報)へのアクセスは行わない。
"""

import io
import zipfile

import extract.railway as railway


class FakeResponse:
    """requests.get()の戻り値の代わりに使うダミーレスポンス"""

    def __init__(self, content):
        self.content = content

    def raise_for_status(self):
        pass


def make_zip_bytes(files):
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        for name, content in files.items():
            zf.writestr(name, content)
    return buf.getvalue()


def test_fetch_railway_geojson_filters_out_non_geojson_files(monkeypatch):
    """shapefile本体やメタデータXMLなど、.geojson以外のファイルは無視する"""
    zip_bytes = make_zip_bytes({
        "utf8/N02-23_RailroadSection.geojson": b'{"type": "FeatureCollection", "features": []}',
        "utf8/N02-23_Station.geojson": b'{"type": "FeatureCollection", "features": []}',
        "N02-23.shp": b"dummy-shapefile-body",
        "N02-23.xml": b"<metadata></metadata>",
    })
    monkeypatch.setattr(railway, "load_page", lambda url: FakeResponse(zip_bytes))

    result = railway.fetch_railway_geojson("23")

    assert set(result.keys()) == {
        "utf8/N02-23_RailroadSection.geojson",
        "utf8/N02-23_Station.geojson",
    }
    assert result["utf8/N02-23_Station.geojson"] == b'{"type": "FeatureCollection", "features": []}'


def test_fetch_railway_geojson_returns_empty_dict_when_no_geojson_present(monkeypatch):
    zip_bytes = make_zip_bytes({"N02-23.shp": b"dummy-shapefile-body"})
    monkeypatch.setattr(railway, "load_page", lambda url: FakeResponse(zip_bytes))

    result = railway.fetch_railway_geojson("23")

    assert result == {}


def test_fetch_railway_geojson_uses_year_code_in_url(monkeypatch):
    captured_urls = []

    def fake_load_page(url):
        captured_urls.append(url)
        return FakeResponse(make_zip_bytes({}))

    monkeypatch.setattr(railway, "load_page", fake_load_page)

    railway.fetch_railway_geojson("24")

    assert captured_urls == ["https://nlftp.mlit.go.jp/ksj/gml/data/N02/N02-24/N02-24_GML.zip"]
