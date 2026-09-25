"""保存済みの生データCSVの物件名だけをLLMで正規化し、変換前後を表示するお試し用スクリプト。

load.pyのようにスクレイピングやジオコーディングは行わないので、LLMでの正規化の
結果だけを手早く確認できる。API料金を抑えるため、既定では先頭から50件のみ処理する。

使い方:
    python scripts/try_llm_clean.py data/rawdata/activelist/suumo_20260925.csv
    python scripts/try_llm_clean.py <CSV> --limit 200 --model claude-haiku-4-5

結果はtransform/llm_clean.pyと同じキャッシュ(data/cache/building_name_cache.json)に
保存されるため、ここで正規化した物件名はload.py実行時にAPIを再度呼ばない。
"""

import argparse
import sys
from pathlib import Path

import pandas as pd

# scripts/配下から直接実行された場合でもリポジトリルート直下のtransformパッケージを
# importできるよう、リポジトリルートをsys.pathへ明示的に追加する。
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from transform.llm_clean import DEFAULT_MODEL, normalize_building_names, rule_based_clean


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("csv", help="nameカラムを持つ生データCSV(load.pyがdata/rawdata/に保存したもの)")
    parser.add_argument("--limit", type=int, default=50, help="処理するユニークな物件名の件数(既定: 50)")
    parser.add_argument("--model", default=DEFAULT_MODEL, help=f"使うモデル(既定: {DEFAULT_MODEL})")
    args = parser.parse_args()

    names = pd.read_csv(args.csv)["name"].dropna().drop_duplicates().head(args.limit).tolist()
    building_names = normalize_building_names(names, model=args.model)

    changed_by_llm = 0
    for name, building_name in zip(names, building_names):
        by_llm = building_name != rule_based_clean(name)
        changed_by_llm += by_llm
        print(f"{'*' if by_llm else ' '} {name}  ->  {building_name}")

    print(f"\n{len(names)}件中{changed_by_llm}件がルールだけの結果と異なります(*印)")
    print(f"ユニークな建物名: {len(set(building_names))}件")


if __name__ == "__main__":
    main()
