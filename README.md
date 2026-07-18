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
uv run streamlit run app_estate.py
uv run streamlit run analytics.py
```

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
