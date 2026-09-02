"""mansion-review.jpのHTML構造を調査するための単発デバッグスクリプト。

extract/mansionreview.py が依存しているセレクタが今も有効かどうかを直接
チェックして報告する。パイプライン本体(extract/)の一部ではなく、構造変化を
調査するための使い捨てツールとしてscripts/に置く。

使い方:
    python scripts/inspect_mansionreview_html.py
    python scripts/inspect_mansionreview_html.py --url https://www.mansion-review.jp/mansion/city/660.html
    python scripts/inspect_mansionreview_html.py --save mansionreview_659.html
"""

import argparse
import sys
from collections import Counter
from pathlib import Path

# scripts/配下から直接実行された場合でもリポジトリルート直下のextractパッケージを
# importできるよう、リポジトリルートをsys.pathへ明示的に追加する。
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from bs4 import BeautifulSoup

import extract.mansionreview as mansionreview
from extract.utils import load_page

# extract/mansionreview.py が依存しているセレクタ一覧
EXPECTED_SELECTORS = [
    ("li", "property-detail-list-item"),
    ("h2", "property-detail-content__head-title"),
    ("table", "property-detail-content_main"),
    ("table", "property-detail-content_sub"),
    ("table", "recommendTable"),
    ("li", "c-pagination-list__item"),
]

DEFAULT_URL = "https://www.mansion-review.jp/mansion/city/659.html"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", default=DEFAULT_URL, help="調査対象のURL")
    parser.add_argument("--save", help="取得した生HTMLを保存するファイルパス(任意)")
    args = parser.parse_args()

    print(f"fetching: {args.url}")
    response = load_page(args.url)
    print(f"status_code: {response.status_code}, content length: {len(response.content)} bytes")

    if args.save:
        with open(args.save, "wb") as f:
            f.write(response.content)
        print(f"saved raw html to: {args.save}")

    soup = BeautifulSoup(response.content, "html.parser")

    print("\n=== extract/mansionreview.py が依存しているセレクタの存在チェック ===")
    for tag, class_name in EXPECTED_SELECTORS:
        found = soup.find_all(tag, class_=class_name)
        status = "OK" if found else "NG (見つかりません)"
        print(f'  <{tag} class="{class_name}"> -> {len(found)}件  [{status}]')

    print("\n=== extract.mansionreview.scrap_from_search()を実際に呼び出した結果 ===")
    try:
        results = mansionreview.scrap_from_search(args.url)
        print(f"  parsed rows: {len(results)}")
        if results:
            print(f"  first row: {results[0]}")
        else:
            print("  0件でした。セレクタ自体はOKなので、行のtd数不一致など下の詳細チェックを確認してください。")
    except mansionreview.MansionReviewScrapeError as e:
        print(f"  MansionReviewScrapeError: {e}")
    except Exception as e:
        import traceback
        print(f"  ERROR: {type(e).__name__}: {e}")
        traceback.print_exc()

    print("\n=== recommendTableの構造チェック(1物件あたりの個数・行のtd数) ===")
    print("(scrap_from_searchは1物件目に見つかったrecommendTableだけを使い、各行のtd数が9でないと")
    print(" その行を無言でスキップします。9件でない行が多い場合はここが0件の原因です)")
    tables_per_bukken_counter = Counter()
    td_count_counter = Counter()
    for bukken in soup.find_all("li", class_="property-detail-list-item"):
        tables = bukken.find_all("table", class_="recommendTable")
        tables_per_bukken_counter[len(tables)] += 1
        if not tables:
            continue
        for tr in tables[0].find_all("tr")[1:]:
            td_count_counter[len(tr.find_all("td"))] += 1
    print(f"  1物件あたりのrecommendTable数の分布: {dict(sorted(tables_per_bukken_counter.items()))}")
    print("  1つ目のrecommendTable内の各行のtd数の分布:")
    for count, freq in sorted(td_count_counter.items()):
        marker = "" if count == 9 else "  <- 想定(9)と不一致。この行は今スキップされています"
        print(f"    td数={count}: {freq}行{marker}")

    print("\n=== ページ内に存在するclass名の一覧(出現回数上位50件) ===")
    print("(上のNGと似た名前があれば、それがリネーム後の候補です)")
    class_counter = Counter()
    for tag in soup.find_all(class_=True):
        for cls in tag.get("class", []):
            class_counter[cls] += 1
    for cls, count in class_counter.most_common(50):
        print(f"  {count:>4}  {cls}")


if __name__ == "__main__":
    main()
