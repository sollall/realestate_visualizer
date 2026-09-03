"""extract/utils.pyのsearch_address()が、外部API(国土地理院)の異常応答で
パイプライン全体をクラッシュさせずに済むことを確認するテスト。実際の外部
APIへのアクセスは行わない。
"""

import extract.utils as utils


class FakeResponse:
    """requests.get()の戻り値の代わりに使うダミーレスポンス"""

    def __init__(self, json_result=None, json_error=None):
        self._json_result = json_result
        self._json_error = json_error

    def json(self):
        if self._json_error is not None:
            raise self._json_error
        return self._json_result


def test_search_address_returns_none_when_response_is_not_json(monkeypatch):
    """レート制限等でJSON以外(HTMLエラーページ等)が返ってきても例外を送出しない"""
    monkeypatch.setattr(
        utils, "load_page",
        lambda url: FakeResponse(json_error=ValueError("Expecting value: line 1 column 1 (char 0)")),
    )

    lon, lat = utils.search_address("東京都テスト区1-1-1")

    assert (lon, lat) == (None, None)


def test_search_address_returns_none_when_no_match_found(monkeypatch):
    """該当する住所が見つからず空配列が返ってきても例外を送出しない"""
    monkeypatch.setattr(utils, "load_page", lambda url: FakeResponse(json_result=[]))

    lon, lat = utils.search_address("存在しない住所")

    assert (lon, lat) == (None, None)


def test_search_address_returns_coordinates_when_found(monkeypatch):
    monkeypatch.setattr(
        utils, "load_page",
        lambda url: FakeResponse(json_result=[{"geometry": {"coordinates": [139.7, 35.6]}}]),
    )

    lon, lat = utils.search_address("東京都テスト区1-1-1")

    assert (lon, lat) == (139.7, 35.6)
