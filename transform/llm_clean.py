"""物件名から広告文句を取り除いて建物名に正規化する(LLMを使う生データ加工処理)。

SUUMOの物件名は「【リノベ済】パークハウス〇〇 3階 南向き」のように広告文句や
部屋の情報が混ざっており、同じ建物でも表記がばらばらになる。ルールだけでは
取り切れないため、ルールで下処理したうえでLLM(Claude)に建物名だけを抜き出させる。

- 結果は元の物件名をキーにJSONファイルへキャッシュし、同じ物件名でAPIを再度呼ばない
- LLMの出力が元の物件名に含まれない(=作文した)場合は採用せず、ルールでの結果を使う
- APIが使えない・エラーになった場合もルールでの結果にフォールバックする
"""

import json
import os
import re
import unicodedata
from pathlib import Path

from pydantic import BaseModel

DEFAULT_CACHE_PATH = Path("data/cache/building_name_cache.json")
DEFAULT_MODEL = os.environ.get("REALESTATE_LLM_MODEL", "claude-opus-5")
BATCH_SIZE = 50

SYSTEM_PROMPT = """あなたは不動産ポータルサイトの物件名から建物名だけを取り出すアシスタントです。
各物件名について、建物(マンション)の名称だけを返してください。

- 「リノベーション済」「ペット可」「南向き」「角部屋」などの広告文句や、階数・号室・間取りは取り除く
- 建物名そのものの表記(カタカナ・漢字・英字・棟名)は変えない。言い換え・補完・翻訳はしない
- 建物名が読み取れない場合は、入力をそのまま返す
- 入力と同じ index を付けて、すべての物件名について返す"""


class BuildingName(BaseModel):
    index: int
    building_name: str


class BuildingNames(BaseModel):
    items: list[BuildingName]


class BuildingNameCache:
    """物件名->建物名の正規化結果をJSONファイルに永続化するキャッシュ"""

    def __init__(self, cache_path=DEFAULT_CACHE_PATH):
        self.cache_path = Path(cache_path)
        self._data = self._load()

    def _load(self):
        if not self.cache_path.exists():
            return {}
        with open(self.cache_path, encoding="utf-8") as f:
            return json.load(f)

    def save(self):
        self.cache_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.cache_path, "w", encoding="utf-8") as f:
            json.dump(self._data, f, ensure_ascii=False)

    def __contains__(self, name):
        return name in self._data

    def get(self, name):
        return self._data.get(name)

    def set(self, name, building_name):
        self._data[name] = building_name


def rule_based_clean(name):
    """LLMを使わずに落とせる表記ゆれ・広告文句を取り除く"""
    name = unicodedata.normalize("NFKC", name)
    # 【リノベ済】[ペット可]などの括弧書きは広告文句であることがほとんど
    name = re.sub(r"【[^】]*】|\[[^\]]*\]|≪[^≫]*≫|<[^>]*>", " ", name)
    return re.sub(r"\s+", " ", name).strip()


def _compact(text):
    return re.sub(r"\s+", "", text)


def is_grounded(candidate, source):
    """LLMの出力が元の物件名の一部になっているか(作文していないか)を確認する"""
    candidate = _compact(unicodedata.normalize("NFKC", candidate))
    return bool(candidate) and candidate in _compact(source)


def _ask_llm(client, names, model):
    """物件名のリストをLLMに渡し、index->建物名のdictを返す"""
    payload = "\n".join(json.dumps({"index": i, "name": n}, ensure_ascii=False) for i, n in enumerate(names))
    response = client.messages.parse(
        model=model,
        max_tokens=16000,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": payload}],
        output_config={"effort": "low"},
        output_format=BuildingNames,
    )
    if response.stop_reason != "end_turn" or response.parsed_output is None:
        return {}
    return {item.index: item.building_name for item in response.parsed_output.items}


def normalize_building_names(names, client=None, cache_path=DEFAULT_CACHE_PATH, model=DEFAULT_MODEL, batch_size=BATCH_SIZE):
    """物件名のリストを建物名のリストに正規化する(入力と同じ順序・長さで返す)"""
    cache = BuildingNameCache(cache_path)
    names_to_fetch = sorted({n for n in names if n not in cache})

    if names_to_fetch:
        if client is None:
            import anthropic
            client = anthropic.Anthropic()

        for start in range(0, len(names_to_fetch), batch_size):
            batch = names_to_fetch[start:start + batch_size]
            cleaned = [rule_based_clean(n) for n in batch]
            try:
                results = _ask_llm(client, cleaned, model)
            except Exception as e:
                # APIエラーでパイプライン全体を止めず、この回はルールの結果を使う
                print(f"建物名の正規化でLLMの呼び出しに失敗しました: {e}")
                results = {}

            for i, name in enumerate(batch):
                candidate = results.get(i)
                # 作文された・取得できなかったものは次回再トライできるよう、キャッシュには書き込まない
                if candidate is not None and is_grounded(candidate, cleaned[i]):
                    cache.set(name, unicodedata.normalize("NFKC", candidate).strip())

            cache.save()

    return [cache.get(n) or rule_based_clean(n) for n in names]
