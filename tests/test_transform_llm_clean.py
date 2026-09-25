"""transform/llm_clean.pyの建物名正規化が、キャッシュでAPI呼び出しを減らし、
LLMの作文やAPIエラーをルールベースの結果で吸収できることを確認するテスト。
実際のAPIへのアクセスは行わない。"""

import json
from types import SimpleNamespace

import transform.llm_clean as llm_clean


class FakeMessages:
    def __init__(self, answer, stop_reason="end_turn", error=None):
        self.answer = answer
        self.stop_reason = stop_reason
        self.error = error
        self.calls = []

    def parse(self, **kwargs):
        self.calls.append(kwargs)
        if self.error is not None:
            raise self.error
        names = [json.loads(line)["name"] for line in kwargs["messages"][0]["content"].splitlines()]
        items = [llm_clean.BuildingName(index=i, building_name=self.answer(n)) for i, n in enumerate(names)]
        return SimpleNamespace(stop_reason=self.stop_reason, parsed_output=llm_clean.BuildingNames(items=items))


class FakeClient:
    def __init__(self, **kwargs):
        self.messages = FakeMessages(**kwargs)


def strip_after_space(name):
    return name.split(" ")[0]


def test_rule_based_clean_removes_bracketed_ads_and_normalizes_width():
    assert llm_clean.rule_based_clean("【リノベ済】パークハウス三田　ＡＢＣ") == "パークハウス三田 ABC"


def test_is_grounded():
    assert llm_clean.is_grounded("パークハウス 三田", "パークハウス三田 3階")
    assert not llm_clean.is_grounded("パークタワー三田", "パークハウス三田 3階")
    assert not llm_clean.is_grounded("", "パークハウス三田")


def test_normalize_uses_llm_result_and_dedupes(tmp_path):
    client = FakeClient(answer=strip_after_space)
    names = ["【新着】パークハウス三田 3階 南向き", "パークハウス三田 角部屋", "【新着】パークハウス三田 3階 南向き"]

    result = llm_clean.normalize_building_names(names, client=client, cache_path=tmp_path / "c.json")

    assert result == ["パークハウス三田", "パークハウス三田", "パークハウス三田"]
    assert len(client.messages.calls) == 1


def test_normalize_skips_api_for_cached_names(tmp_path):
    cache_path = tmp_path / "c.json"
    cache_path.write_text(json.dumps({"パークハウス三田 3階": "パークハウス三田"}), encoding="utf-8")
    client = FakeClient(answer=strip_after_space)

    result = llm_clean.normalize_building_names(["パークハウス三田 3階"], client=client, cache_path=cache_path)

    assert result == ["パークハウス三田"]
    assert client.messages.calls == []


def test_normalize_rejects_hallucinated_names_and_does_not_cache(tmp_path):
    cache_path = tmp_path / "c.json"
    client = FakeClient(answer=lambda n: "存在しないマンション")

    result = llm_clean.normalize_building_names(["【新着】パークハウス三田"], client=client, cache_path=cache_path)

    assert result == ["パークハウス三田"]
    assert json.loads(cache_path.read_text()) == {}


def test_normalize_falls_back_to_rules_on_api_error(tmp_path):
    client = FakeClient(answer=strip_after_space, error=RuntimeError("overloaded"))

    result = llm_clean.normalize_building_names(["【新着】パークハウス三田"], client=client, cache_path=tmp_path / "c.json")

    assert result == ["パークハウス三田"]


def test_normalize_ignores_truncated_response(tmp_path):
    client = FakeClient(answer=strip_after_space, stop_reason="max_tokens")

    result = llm_clean.normalize_building_names(["パークハウス三田 3階"], client=client, cache_path=tmp_path / "c.json")

    assert result == ["パークハウス三田 3階"]


def test_normalize_batches_requests(tmp_path):
    client = FakeClient(answer=strip_after_space)
    names = [f"物件{i} 1階" for i in range(5)]

    result = llm_clean.normalize_building_names(names, client=client, cache_path=tmp_path / "c.json", batch_size=2)

    assert result == [f"物件{i}" for i in range(5)]
    assert len(client.messages.calls) == 3
