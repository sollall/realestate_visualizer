# セットアップ

依存関係の管理には [uv](https://docs.astral.sh/uv/) を使用しています。

```
uv sync
```

# データの取得

`load.py`にサイト名を指定して実行すると、該当サイトの`extract`→`transform`が実行され、
`data/rawdata/`に生データ、`data/analytics/`に分析用データがCSVで保存されます。
対応サイト名は`pipelines/registry.py`の`PIPELINES`を参照してください。

```
uv run python load.py suumo
uv run python load.py mansionreview
```

# appの起動

```
uv run streamlit run Home.py
```

`Home.py` がメイン画面で、`pages/` 配下の各ページ(analytics, app_estate, plateau, price3d)がサイドバーから選択できます。

`plateau`ページはPLATEAUの3D都市モデルデータセットを利用します。初回は以下のコマンドで
対象データセット(`plateau-13106-taito-ku-2023`)をローカルにインストールしてください。

```
uv run plateaukit install plateau-13106-taito-ku-2023
```

# テスト

```
uv run pytest
```

`load.py`は実サイトへスクレイピングを行うため、CI/自動テストでは実サイトを叩く代わりに
`tests/test_load.py`でダミーのPipelineに差し替えて`extract`→検証→保存→`transform`→保存の
一連の流れが正しく動くことを確認しています。push/PR時に`.github/workflows/ci.yml`で自動実行されます。

# リポジトリ構造

データの取得・加工(IF+生データ加工)と、可視化・分析(streamlit)を疎結合にする方針で構成しています。
可視化側は`data/analytics/`配下のCSVというインターフェース越しにのみデータ取得・加工側とつながっており、
互いの実装の詳細(スクレイピング方法やDataFrameの中間表現など)には依存しません。

- `extract/` … 外部サイト・外部API(ジオコーディング等)へのアクセスのみを担うIF層
- `transform/` … `extract`が返す生データを分析用データに加工する層(重複除去・ジオコーディング付与など)
- `pipelines/` … サイトごとに`extract`+`transform`をまとめて実行するオーケストレーション層(`Pipeline`基底クラス)
- `load.py` … `pipelines`を呼び出すCLIエントリポイント。`data/rawdata/`に生データ、`data/analytics/`に加工済みデータを保存する
- `analysis/` … 可視化・分析(pages)側が共通で使うロジック(CSV読み込み、絞り込み、色計算)と、分析データが満たすべきスキーマ(`analysis/schema.py`)
- `pages/` … streamlitの各画面。`analysis/`経由で`data/analytics/`配下のデータを読み込んで可視化するだけの薄い層
- `data/`
  - `rawdata/` … `extract`直後の生データ
  - `analytics/` … `transform`後の分析用データ(pagesはここだけを参照する)
