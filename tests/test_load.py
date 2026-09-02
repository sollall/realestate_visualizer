"""load.pyのオーケストレーション(extract -> validate -> 保存 -> transform -> 保存)を、
実サイトへのスクレイピングを行わずに検証するテスト。
"""

import pandas as pd
import pytest

import load
from pipelines.core.pipeline import Pipeline
from pipelines.registry import PIPELINES


class FakePipeline(Pipeline):
    """ネットワークアクセスなしでload.pyの一連の流れを検証するためのダミーパイプライン"""

    def extract(self):
        return pd.DataFrame({
            "name": ["Test Mansion"],
            "price": [50000000],
            "address": ["Tokyo, Japan"],
            "area": [100.0],
            "age": [5],
        })

    def transform(self, data):
        data = data.copy()
        data["坪単価"] = data["price"] / data["area"]
        data["lons"] = 139.7
        data["lats"] = 35.6
        return data


class InvalidRawPipeline(Pipeline):
    """extract結果が必須カラムを満たさないケースを再現するダミーパイプライン"""

    def extract(self):
        return pd.DataFrame({"name": ["Test Mansion"]})

    def transform(self, data):
        return data


def _prepare_data_dirs(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "data/rawdata/activelist").mkdir(parents=True)
    (tmp_path / "data/analytics/activelist").mkdir(parents=True)


def test_main_saves_raw_and_analytics_csv(tmp_path, monkeypatch):
    _prepare_data_dirs(tmp_path, monkeypatch)
    monkeypatch.setitem(load.PIPELINES, "fake", FakePipeline)

    load.main("fake")

    raw_files = list((tmp_path / "data/rawdata/activelist").glob("fake_*.csv"))
    analytics_files = list((tmp_path / "data/analytics/activelist").glob("fake_*.csv"))
    assert len(raw_files) == 1
    assert len(analytics_files) == 1

    raw_df = pd.read_csv(raw_files[0], index_col=0)
    assert list(raw_df["name"]) == ["Test Mansion"]

    analytics_df = pd.read_csv(analytics_files[0], index_col=0)
    assert "坪単価" in analytics_df.columns
    assert "lons" in analytics_df.columns


def test_main_raises_on_invalid_raw_data(tmp_path, monkeypatch):
    _prepare_data_dirs(tmp_path, monkeypatch)
    monkeypatch.setitem(load.PIPELINES, "invalid", InvalidRawPipeline)

    with pytest.raises(ValueError):
        load.main("invalid")

    # 生データのバリデーションで落ちるので、CSVは一切書き出されない
    assert list((tmp_path / "data/rawdata/activelist").glob("*.csv")) == []


def test_main_raises_on_unknown_site():
    with pytest.raises(ValueError):
        load.main("unknown-site")


def test_registered_pipelines_are_instantiable():
    """実際に登録されている各サイトのPipelineがextract/transformを実装した
    インスタンス化可能なクラスであることを確認する(ネットワークは呼ばない)"""
    for site_name, pipeline_cls in PIPELINES.items():
        pipeline = pipeline_cls()
        assert isinstance(pipeline, Pipeline), site_name
