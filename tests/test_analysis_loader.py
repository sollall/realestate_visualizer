"""analysis/loader.pyのload_railway_geojson()が、scripts/fetch_railway_data.pyの
出力ファイル名(...RailroadSection.geojson / ...Station.geojson)を正しく
路線用・駅用に分類できることを確認するテスト。
"""

import json

import analysis.loader as loader


def test_load_railway_geojson_returns_none_when_directory_missing(monkeypatch, tmp_path):
    monkeypatch.setattr(loader, "RAILWAY_ROOT", str(tmp_path / "not-exist"))

    lines, stations = loader.load_railway_geojson()

    assert lines is None
    assert stations is None


def test_load_railway_geojson_classifies_files_by_name(monkeypatch, tmp_path):
    monkeypatch.setattr(loader, "RAILWAY_ROOT", str(tmp_path))

    lines_data = {"type": "FeatureCollection", "features": ["line"]}
    stations_data = {"type": "FeatureCollection", "features": ["station"]}
    (tmp_path / "N02-23_RailroadSection.geojson").write_text(json.dumps(lines_data), encoding="utf-8")
    (tmp_path / "N02-23_Station.geojson").write_text(json.dumps(stations_data), encoding="utf-8")
    (tmp_path / "N02-23.xml").write_text("<metadata></metadata>", encoding="utf-8")

    lines, stations = loader.load_railway_geojson()

    assert lines == lines_data
    assert stations == stations_data


def test_load_railway_geojson_returns_none_for_missing_kind(monkeypatch, tmp_path):
    monkeypatch.setattr(loader, "RAILWAY_ROOT", str(tmp_path))

    stations_data = {"type": "FeatureCollection", "features": []}
    (tmp_path / "N02-23_Station.geojson").write_text(json.dumps(stations_data), encoding="utf-8")

    lines, stations = loader.load_railway_geojson()

    assert lines is None
    assert stations == stations_data
