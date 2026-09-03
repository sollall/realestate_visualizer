"""transform/geocode.pyの住所キャッシュが、重複住所の再問い合わせを避け、
外部API(国土地理院)へのアクセスを減らせていることを確認するテスト。
実際のAPIへのアクセス・実際のmultiprocessingは行わない。
"""

import json

import transform.geocode as geocode


class FakePool:
    """実際にmultiprocessingを使わず、同一プロセス内で逐次実行するダミーPool"""

    def __init__(self, *args, **kwargs):
        pass

    def __enter__(self):
        return self

    def __exit__(self, *exc_info):
        return False

    def imap(self, func, iterable):
        return (func(item) for item in iterable)


def test_geocode_cache_set_get_contains(tmp_path):
    cache = geocode.GeocodeCache(tmp_path / "cache.json")

    assert "東京都A区1-1" not in cache
    assert cache.get("東京都A区1-1") is None

    cache.set("東京都A区1-1", 139.0, 35.0)

    assert "東京都A区1-1" in cache
    assert cache.get("東京都A区1-1") == (139.0, 35.0)


def test_geocode_cache_persists_across_instances(tmp_path):
    cache_path = tmp_path / "cache.json"

    cache = geocode.GeocodeCache(cache_path)
    cache.set("東京都A区1-1", 139.0, 35.0)
    cache.save()

    reloaded = geocode.GeocodeCache(cache_path)

    assert reloaded.get("東京都A区1-1") == (139.0, 35.0)


def test_get_lat_lon_dedupes_and_calls_search_address_once_per_unique_address(monkeypatch, tmp_path):
    monkeypatch.setattr(geocode, "Pool", FakePool)

    call_log = []

    def fake_search_address(address):
        call_log.append(address)
        return (139.0, 35.0)

    monkeypatch.setattr(geocode, "search_address", fake_search_address)

    addresses = ["東京都A区1-1", "東京都B区2-2", "東京都A区1-1", "東京都A区1-1"]
    cache_path = tmp_path / "cache.json"

    lons, lats = geocode.get_lat_lon(addresses, cache_path=cache_path)

    assert sorted(call_log) == ["東京都A区1-1", "東京都B区2-2"]
    assert lons == [139.0, 139.0, 139.0, 139.0]
    assert lats == [35.0, 35.0, 35.0, 35.0]


def test_get_lat_lon_uses_persisted_cache_and_skips_api_call(monkeypatch, tmp_path):
    monkeypatch.setattr(geocode, "Pool", FakePool)

    cache_path = tmp_path / "cache.json"
    cache_path.write_text(json.dumps({"東京都A区1-1": [139.0, 35.0]}), encoding="utf-8")

    def fail_if_called(address):
        raise AssertionError(f"キャッシュ済みの住所でAPIが呼ばれた: {address}")

    monkeypatch.setattr(geocode, "search_address", fail_if_called)

    lons, lats = geocode.get_lat_lon(["東京都A区1-1"], cache_path=cache_path)

    assert lons == [139.0]
    assert lats == [35.0]


def test_get_lat_lon_does_not_cache_failed_lookups(monkeypatch, tmp_path):
    monkeypatch.setattr(geocode, "Pool", FakePool)
    monkeypatch.setattr(geocode, "search_address", lambda address: (None, None))

    cache_path = tmp_path / "cache.json"

    lons, lats = geocode.get_lat_lon(["見つからない住所"], cache_path=cache_path)

    assert lons == [None]
    assert lats == [None]
    assert json.loads(cache_path.read_text()) == {}
