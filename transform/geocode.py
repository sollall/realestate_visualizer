"""生データの住所を緯度経度に変換する(extractのgeocoding IFを使う生データ加工処理)。"""

import json
import multiprocessing
from multiprocessing import Pool
from pathlib import Path

from tqdm import tqdm
from extract.utils import search_address

# 住所->[lon,lat]のキャッシュ。同じ建物の複数部屋を別々にジオコーディングし直したり、
# 前回実行分を再度APIに問い合わせたりせずに済ませ、外部APIのレート制限を避ける。
DEFAULT_CACHE_PATH = Path("data/cache/geocode_cache.json")


def _load_cache(cache_path):
    if not cache_path.exists():
        return {}
    with open(cache_path, encoding="utf-8") as f:
        return json.load(f)


def _save_cache(cache_path, cache):
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    with open(cache_path, "w", encoding="utf-8") as f:
        json.dump(cache, f, ensure_ascii=False)


def get_lat_lon(addresses, cache_path=DEFAULT_CACHE_PATH):

    cache = _load_cache(cache_path)

    # 同一建物の複数部屋で住所が重複するため、ユニークかつ未キャッシュの住所のみ問い合わせる
    addresses_to_fetch = sorted({a for a in addresses if a not in cache})

    if addresses_to_fetch:
        with Pool(processes=multiprocessing.cpu_count()) as pool:
            with tqdm(total=len(addresses_to_fetch)) as pbar:
                for address, (lon, lat) in zip(addresses_to_fetch, pool.imap(search_address, addresses_to_fetch)):
                    if lon is not None and lat is not None:
                        cache[address] = [lon, lat]
                    pbar.update(1)

        # 取得できなかった住所は次回再トライできるよう、キャッシュには書き込まない
        _save_cache(cache_path, cache)

    lons=[cache.get(address, [None, None])[0] for address in addresses]
    lats=[cache.get(address, [None, None])[1] for address in addresses]

    return lons,lats