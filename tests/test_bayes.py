"""analysis/bayes.pyのRBF基底のベイズ線形回帰による単価曲面推定を、小さな合成データで検証するテスト。"""

import numpy as np
import pandas as pd

from analysis.bayes import fit_price_surface


def _make_synthetic_data(n_per_side=5, seed=0):
    rng = np.random.default_rng(seed)
    lons, lats = np.meshgrid(
        np.linspace(139.70, 139.80, n_per_side),
        np.linspace(35.60, 35.70, n_per_side),
    )
    lons = lons.ravel()
    lats = lats.ravel()
    # 東(lonsが大きい)ほど坪単価が高くなる、というシンプルな真の関係を仕込む
    base_price = 300 + (lons - lons.min()) * 5000
    noise = rng.normal(scale=5, size=lons.shape)
    price = base_price + noise

    return pd.DataFrame({"lons": lons, "lats": lats, "坪単価": price})


def test_fit_price_surface_returns_expected_columns_and_shape():
    df = _make_synthetic_data()
    grid_size = 6

    grid_df, model = fit_price_surface(df, grid_size=grid_size)

    assert list(grid_df.columns) == ["lons", "lats", "price_mean", "price_std"]
    # データに支持されない(観測点から離れすぎた)グリッド点は除外されうるため <= で確認する
    assert len(grid_df) <= grid_size * grid_size
    assert model is not None


def test_fit_price_surface_grid_covers_padded_data_range():
    df = _make_synthetic_data()

    grid_df, _ = fit_price_surface(df, grid_size=10, padding_ratio=0.1)

    assert grid_df["lons"].min() < df["lons"].min()
    assert grid_df["lons"].max() > df["lons"].max()
    assert grid_df["lats"].min() < df["lats"].min()
    assert grid_df["lats"].max() > df["lats"].max()


def test_fit_price_surface_prices_are_positive():
    df = _make_synthetic_data()

    grid_df, _ = fit_price_surface(df, grid_size=8)

    assert (grid_df["price_mean"] > 0).all()
    assert (grid_df["price_std"] >= 0).all()


def test_fit_price_surface_learns_spatial_trend():
    """東西で坪単価が変わるよう仕込んだデータで、推定平均が同じ傾向を再現するか確認する。"""
    df = _make_synthetic_data()

    grid_df, _ = fit_price_surface(df, grid_size=10)

    west = grid_df[grid_df["lons"] < grid_df["lons"].median()]
    east = grid_df[grid_df["lons"] >= grid_df["lons"].median()]

    assert east["price_mean"].mean() > west["price_mean"].mean()


def test_fit_price_surface_masks_unsupported_far_regions():
    """密集クラスタから離れた外れ値が1点あっても、間の空白域(海や郊外を模した領域)
    まで推定結果で埋めてしまわない(=外挿しすぎない)ことを確認する。"""
    rng = np.random.default_rng(0)
    n = 60
    lons = rng.uniform(139.70, 139.75, n)
    lats = rng.uniform(35.65, 35.70, n)
    price = 400 + rng.normal(scale=10, size=n)
    df = pd.DataFrame({"lons": lons, "lats": lats, "坪単価": price})
    df = pd.concat(
        [df, pd.DataFrame({"lons": [139.45], "lats": [35.80], "坪単価": [350]})],
        ignore_index=True,
    )

    grid_size = 40
    grid_df, _ = fit_price_surface(df, grid_size=grid_size)

    assert len(grid_df) < grid_size * grid_size

    gap_region = grid_df[(grid_df["lons"] < 139.6) & (grid_df["lons"] > 139.5)]
    assert len(gap_region) == 0


def test_fit_price_surface_does_not_extrapolate_wildly():
    """予測値が観測範囲から極端に外れない(基底が疎な領域で暴走しない)ことを確認する。"""
    df = _make_synthetic_data()

    grid_df, _ = fit_price_surface(df, grid_size=20)

    observed_min = df["坪単価"].min()
    observed_max = df["坪単価"].max()
    margin = observed_max - observed_min

    assert grid_df["price_mean"].min() > observed_min - margin
    assert grid_df["price_mean"].max() < observed_max + margin


def _make_synthetic_data_with_age(n=200, seed=0):
    rng = np.random.default_rng(seed)
    lons = rng.uniform(139.70, 139.75, n)
    lats = rng.uniform(35.65, 35.70, n)
    age = rng.uniform(0, 40, n)
    # 築年数が古いほど坪単価が下がる、というシンプルな真の関係を仕込む
    price = 500 - age * 5 + rng.normal(scale=5, size=n)
    return pd.DataFrame({"lons": lons, "lats": lats, "age": age, "坪単価": price})


def test_fit_price_surface_with_extra_column_reproduces_slice_trend():
    """extra_columnsに築年数を加え、断面(slice_values)を変えると
    その属性軸に沿った傾向(古いほど安い)を再現することを確認する。"""
    df = _make_synthetic_data_with_age()

    grid_new, _ = fit_price_surface(
        df, grid_size=15, extra_columns=("age",), slice_values={"age": 5}
    )
    grid_old, _ = fit_price_surface(
        df, grid_size=15, extra_columns=("age",), slice_values={"age": 35}
    )

    assert grid_new["price_mean"].mean() > grid_old["price_mean"].mean()


def test_fit_price_surface_without_slice_values_uses_median():
    """slice_valuesを指定しない場合、extra_columnsの中央値を使った断面になることを確認する。"""
    df = _make_synthetic_data_with_age()

    grid_default, _ = fit_price_surface(df, grid_size=10, extra_columns=("age",))
    grid_median, _ = fit_price_surface(
        df, grid_size=10, extra_columns=("age",), slice_values={"age": df["age"].median()}
    )

    assert np.allclose(grid_default["price_mean"].to_numpy(), grid_median["price_mean"].to_numpy())
