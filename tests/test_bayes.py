"""analysis/bayes.pyのガウス過程による単価曲面推定を、小さな合成データで検証するテスト。"""

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
    assert len(grid_df) == grid_size * grid_size
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
