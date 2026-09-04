"""物件の緯度経度・坪単価から、固定RBF基底のベイズ線形回帰でエリア全体の単価曲面を推定するロジック。

ガウス過程(カーネルをデータから最適化)と違い、あらかじめ空間上に固定した
RBF基底関数の中心に緯度経度を投影してから線形回帰するだけなので、
反復最適化(restart)が不要で閉形式に解け、観測点数が増えても計算量が
ほぼ線形にしか増えない。坪単価は対数正規に近い分布になりやすいため
対数を取って回帰し、予測は指数で坪単価スケールに戻す。
BayesianRidgeは予測の事後分散も返すため、GPと同様に
「観測点が少ないエリアほど推定に自信がない」という不確実性をそのまま可視化に使える。
"""

import numpy as np
import pandas as pd
from sklearn.linear_model import BayesianRidge


def _rbf_centers(X, n_per_side=7):
    """観測データの範囲を覆うグリッド状にRBF基底の中心を配置する。"""
    lon_centers = np.linspace(X[:, 0].min(), X[:, 0].max(), n_per_side)
    lat_centers = np.linspace(X[:, 1].min(), X[:, 1].max(), n_per_side)
    mesh_lon, mesh_lat = np.meshgrid(lon_centers, lat_centers)
    return np.column_stack([mesh_lon.ravel(), mesh_lat.ravel()])


def _rbf_features(X, centers, length_scale):
    """各点を、中心からの距離に基づくRBF基底関数の値に変換する。"""
    sq_dist = ((X[:, None, :] - centers[None, :, :]) ** 2).sum(axis=2)
    return np.exp(-sq_dist / (2 * length_scale ** 2))


def fit_price_surface(df, grid_size=30, padding_ratio=0.1, n_centers_per_side=7):
    """lons/latsを入力、坪単価を出力としてベイズ線形回帰を学習し、グリッド上の推定値を返す。

    Parameters
    ----------
    df : pandas.DataFrame
        "lons", "lats", "坪単価" 列を持つ観測データ。
    grid_size : int
        緯度・経度それぞれの方向の予測グリッド分割数。
    padding_ratio : float
        観測データの範囲に対して、どれだけ外側までグリッドを広げるか。
    n_centers_per_side : int
        RBF基底の中心を配置するグリッドの一辺あたりの数。

    Returns
    -------
    grid_df : pandas.DataFrame
        "lons", "lats", "price_mean"(坪単価の推定平均),
        "price_std"(対数スケールでの予測標準偏差=不確実性)を持つ推定結果。
    model : sklearn.linear_model.BayesianRidge
        学習済みモデル。
    """
    X = df[["lons", "lats"]].to_numpy(dtype=float)
    y = np.log(df["坪単価"].to_numpy(dtype=float))

    centers = _rbf_centers(X, n_per_side=n_centers_per_side)
    # 基底の間隔と同程度の広がりを持たせる(基底同士が滑らかにつながる目安)
    length_scale = (X[:, 0].max() - X[:, 0].min()) / max(n_centers_per_side - 1, 1)
    length_scale = max(length_scale, 1e-6)

    features = _rbf_features(X, centers, length_scale)
    model = BayesianRidge()
    model.fit(features, y)

    lon_min, lon_max = X[:, 0].min(), X[:, 0].max()
    lat_min, lat_max = X[:, 1].min(), X[:, 1].max()
    lon_pad = (lon_max - lon_min) * padding_ratio
    lat_pad = (lat_max - lat_min) * padding_ratio

    lon_grid = np.linspace(lon_min - lon_pad, lon_max + lon_pad, grid_size)
    lat_grid = np.linspace(lat_min - lat_pad, lat_max + lat_pad, grid_size)
    mesh_lon, mesh_lat = np.meshgrid(lon_grid, lat_grid)
    X_grid = np.column_stack([mesh_lon.ravel(), mesh_lat.ravel()])

    grid_features = _rbf_features(X_grid, centers, length_scale)
    mean_log, std_log = model.predict(grid_features, return_std=True)

    grid_df = pd.DataFrame({
        "lons": X_grid[:, 0],
        "lats": X_grid[:, 1],
        "price_mean": np.exp(mean_log),
        "price_std": std_log,
    })

    return grid_df, model
