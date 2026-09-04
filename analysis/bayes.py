"""物件の緯度経度・坪単価から、ガウス過程回帰でエリア全体の単価曲面を推定するロジック。

坪単価は対数正規に近い分布になりやすいため対数を取ってGPを当てはめ、
予測は指数で坪単価スケールに戻す。GPは予測平均だけでなく予測分散も返すため、
「観測点が少ないエリアほど推定に自信がない」という不確実性をそのまま可視化に使える。
"""

import GPy
import numpy as np
import pandas as pd


def fit_price_surface(df, grid_size=30, padding_ratio=0.1):
    """lons/latsを入力、坪単価を出力としてGPを学習し、グリッド上の推定値を返す。

    Parameters
    ----------
    df : pandas.DataFrame
        "lons", "lats", "坪単価" 列を持つ観測データ。
    grid_size : int
        緯度・経度それぞれの方向のグリッド分割数。
    padding_ratio : float
        観測データの範囲に対して、どれだけ外側までグリッドを広げるか。

    Returns
    -------
    grid_df : pandas.DataFrame
        "lons", "lats", "price_mean"(坪単価の推定平均),
        "price_std"(対数スケールでの予測標準偏差=不確実性)を持つ推定結果。
    model : GPy.models.GPRegression
        学習済みモデル。
    """
    X = df[["lons", "lats"]].to_numpy(dtype=float)
    y = np.log(df["坪単価"].to_numpy(dtype=float)).reshape(-1, 1)

    kernel = GPy.kern.RBF(input_dim=2, ARD=True)
    model = GPy.models.GPRegression(X, y, kernel, normalizer=True)
    model.optimize_restarts(num_restarts=5, messages=False, verbose=False)

    lon_min, lon_max = X[:, 0].min(), X[:, 0].max()
    lat_min, lat_max = X[:, 1].min(), X[:, 1].max()
    lon_pad = (lon_max - lon_min) * padding_ratio
    lat_pad = (lat_max - lat_min) * padding_ratio

    lon_grid = np.linspace(lon_min - lon_pad, lon_max + lon_pad, grid_size)
    lat_grid = np.linspace(lat_min - lat_pad, lat_max + lat_pad, grid_size)
    mesh_lon, mesh_lat = np.meshgrid(lon_grid, lat_grid)
    X_grid = np.column_stack([mesh_lon.ravel(), mesh_lat.ravel()])

    mean_log, var_log = model.predict(X_grid)

    grid_df = pd.DataFrame({
        "lons": X_grid[:, 0],
        "lats": X_grid[:, 1],
        "price_mean": np.exp(mean_log.ravel()),
        "price_std": np.sqrt(var_log.ravel()),
    })

    return grid_df, model
