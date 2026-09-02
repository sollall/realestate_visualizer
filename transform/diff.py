"""日次データ同士を比較して新規・消失レコードを抽出する生データ加工処理。"""

import pandas as pd


def get_diff_records(today, yesterday):
    diff = pd.merge(today, yesterday, on=["建物名", "面積"], how="outer", indicator=True).query('_merge != "both"')

    apeared = diff[diff["_merge"] == "left_only"]
    banished = diff[diff["_merge"] == "right_only"]

    return apeared.merge(today, on=["建物名", "面積"], how="left"), banished.merge(yesterday, on=["建物名", "面積"], how="left")
