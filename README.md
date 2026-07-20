# セットアップ

依存関係の管理には [uv](https://docs.astral.sh/uv/) を使用しています。

```
uv sync
```

# データの取得
```
uv run python scrap.py
uv run python mansionreview.py
```
※動作確認してない

# appの起動

```
uv run streamlit run Home.py
```

`Home.py` がメイン画面で、`pages/` 配下の各ページ(analytics, app_estate, plateau, price3d)がサイドバーから選択できます。

リポジトリ構造を考える
- scrap
  - suumo.py
  - mansionreview.py
  - mansionreview history
- data
  - ActiveListings
    - suumoyyyymmdd.csv
    - mansionreview yyyymmd.csv
  - TransactionHistory
    - くらまえ.csv
- analytics
  - streamlit
