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

`Home.py` がメイン画面で、`pages/` 配下の各ページ(analytics, app_estate, osm_view, plateau, price3d)がサイドバーから選択できます。

`osm_view`ページでは、売り出し中の物件の位置・階数から周囲を一人称視点で眺められます。
周辺の建物・道路・鉄道・水域・緑地はOpenStreetMap(Overpass API)からその場で取得し(1日キャッシュ)、
deck.gl(CDNから読み込み)で描画します。そのため実行環境から`overpass-api.de`と`unpkg.com`に
アクセスできる必要があります。

- 視点の高さは「階数」から(n-1)×3m+1.5m(目線)で計算します。階数や「向き」の列がある
  データ(mansionreview)ではそれが初期値になり、無い場合はサイドバーで指定します。
- OSMの建物は高さ(`height`)や階数(`building:levels`)のタグが無いものが多く、その場合は
  「詳細設定」で指定した高さ(既定6m)で描画します(灰色の建物が推定値)。
- 物件の位置を含む建物は、視点が壁の内側に入らないよう非表示にしています。

`plateau`ページはPLATEAUの3D都市モデルデータセットを利用します。サイドバーの「対象の区」で
東京23区から表示したい区を選べます。選んだ区のデータセットが未インストールの場合は
エラーメッセージにインストールコマンドが表示されるので、それに従ってインストールして
ください(区とデータセットIDの対応は`pages/plateau.py`の`WARD_DATASETS`を参照)。例えば
台東区の場合は以下の通りです。

```
uv run plateaukit install plateau-13106-taito-ku-2024
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

- `extract/` … 外部サイト・外部API(ジオコーディング等)へのアクセスのみを担うIF層。例外として`extract/osm.py`(Overpass API)は`osm_view`ページから物件ごとにその場で呼び出す
- `transform/` … `extract`が返す生データを分析用データに加工する層(重複除去・ジオコーディング付与など)
- `pipelines/` … サイトごとに`extract`+`transform`をまとめて実行するオーケストレーション層(`Pipeline`基底クラス)
- `load.py` … `pipelines`を呼び出すCLIエントリポイント。`data/rawdata/`に生データ、`data/analytics/`に加工済みデータを保存する
- `analysis/` … 可視化・分析(pages)側が共通で使うロジック(CSV読み込み、絞り込み、色計算)と、分析データが満たすべきスキーマ(`analysis/schema.py`)
- `pages/` … streamlitの各画面。`analysis/`経由で`data/analytics/`配下のデータを読み込んで可視化するだけの薄い層
- `data/`
  - `rawdata/` … `extract`直後の生データ
  - `analytics/` … `transform`後の分析用データ(pagesはここだけを参照する)
