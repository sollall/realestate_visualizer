"""物件の緯度経度・坪単価から、固定RBF基底のベイズ線形回帰でエリア全体の単価曲面を推定するロジック。

ガウス過程(カーネルをデータから最適化)と違い、あらかじめ空間上に固定した
RBF基底関数の中心に緯度経度を投影してから線形回帰するだけなので、
反復最適化(restart)が不要で閉形式に解け、観測点数が増えても計算量が
ほぼ線形にしか増えない。坪単価は対数正規に近い分布になりやすいため
対数を取って回帰し、予測は指数で坪単価スケールに戻す。
BayesianRidgeは予測の事後分散も返すため、GPと同様に
「観測点が少ないエリアほど推定に自信がない」という不確実性をそのまま可視化に使える。

基底の中心は緯度経度の範囲全体に一様に敷くのではなく、観測データの分布に
合わせてk-meansで配置する。これにより海上や郊外など物件が存在しない
エリアに基底の影響が及ばなくなる。それでも回帰は線形結合である以上、
観測点から離れた場所では値が不当に高く/低く外挿されうるため、
最寄りの観測点までの距離が典型的な観測点間隔から大きく離れたグリッド点は
「データに支持されていない」として予測結果から除外する。
"""

import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.linear_model import BayesianRidge
from sklearn.neighbors import NearestNeighbors


def _rbf_centers(X, n_centers):
    """観測データの分布(密度)に合わせてk-meansでRBF基底の中心を配置する。"""
    n_centers = min(n_centers, len(X))
    kmeans = KMeans(n_clusters=n_centers, n_init=10, random_state=0)
    kmeans.fit(X)
    return kmeans.cluster_centers_


def _rbf_features(X, centers, length_scale):
    """各点を、中心からの距離に基づくRBF基底関数の値に変換する。"""
    sq_dist = ((X[:, None, :] - centers[None, :, :]) ** 2).sum(axis=2)
    return np.exp(-sq_dist / (2 * length_scale ** 2))


def fit_price_surface(
    df,
    grid_size=30,
    padding_ratio=0.1,
    n_centers_per_side=7,
    unsupported_distance_factor=3.0,
):
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
        RBF基底の中心の目安数(一辺あたり)。実際の中心数は
        n_centers_per_side ** 2 個をk-meansで配置する。
    unsupported_distance_factor : float
        観測点同士の典型的な間隔の何倍まで離れたグリッド点を
        「データに支持されている」とみなすか。これより離れた点は
        外挿の信頼性が低いため結果から除外する。

    Returns
    -------
    grid_df : pandas.DataFrame
        "lons", "lats", "price_mean"(坪単価の推定平均),
        "price_std"(対数スケールでの予測標準偏差=不確実性)を持つ推定結果。
        観測点から離れすぎたグリッド点は含まれない。
    model : sklearn.linear_model.BayesianRidge
        学習済みモデル。
    """
    X = df[["lons", "lats"]].to_numpy(dtype=float)
    y = np.log(df["坪単価"].to_numpy(dtype=float))

    centers = _rbf_centers(X, n_centers=n_centers_per_side ** 2)
    # 基底同士の典型的な間隔と同程度の広がりを持たせる(基底が滑らかにつながる目安)
    center_neighbors = NearestNeighbors(n_neighbors=2).fit(centers)
    center_dists, _ = center_neighbors.kneighbors(centers)
    length_scale = max(np.median(center_dists[:, 1]), 1e-6)

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

    # 観測点同士の典型的な間隔(自分自身を除いた最近傍距離の中央値)を基準に、
    # そこから離れすぎたグリッド点(海上・郊外など物件が存在しないエリア)を除外する
    data_neighbors = NearestNeighbors(n_neighbors=min(2, len(X))).fit(X)
    self_dists, _ = data_neighbors.kneighbors(X)
    typical_spacing = np.median(self_dists[:, -1]) if self_dists.shape[1] > 1 else 0.0
    support_threshold = typical_spacing * unsupported_distance_factor

    nearest_obs_dist, _ = data_neighbors.kneighbors(X_grid, n_neighbors=1)
    is_supported = nearest_obs_dist[:, 0] <= support_threshold if support_threshold > 0 else np.ones(len(X_grid), dtype=bool)

    X_grid = X_grid[is_supported]
    grid_features = _rbf_features(X_grid, centers, length_scale)
    mean_log, std_log = model.predict(grid_features, return_std=True)

    grid_df = pd.DataFrame({
        "lons": X_grid[:, 0],
        "lats": X_grid[:, 1],
        "price_mean": np.exp(mean_log),
        "price_std": std_log,
    })

    return grid_df, model
