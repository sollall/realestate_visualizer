"""可視化・分析側が要求する分析用データの契約(スキーマ)。

extract/transform側(pipelines)はこのスキーマを満たすデータを作る責務を持ち、
pages側はこのスキーマを前提にデータを扱う。
双方がこのモジュールに依存することで、extract/transformとpages側の直接的な
結合を避ける。
"""

# 可視化(streamlit)側の表示に必要なカラム
REQUIRED_COLUMNS = ["address", "area", "age", "lons", "lats", "坪単価"]
