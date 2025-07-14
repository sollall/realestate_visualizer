# データの取得
```
python scrap.py
python mansionreview.py
```
※動作確認してない

# appの起動

```
streamlit run app_estate.py
streamlit run analytics.py
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
