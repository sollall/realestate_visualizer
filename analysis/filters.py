"""pages側で繰り返し使う絞り込みロジック。"""


def filter_range(df, column, value_range):
    """dfをcolumnがvalue_range=(min, max)に収まる行だけに絞り込む。"""
    min_value, max_value = value_range
    return df[(df[column] >= min_value) & (df[column] <= max_value)]
