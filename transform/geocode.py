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


class GeocodeCache:
    """住所->[lon,lat]のジオコーディング結果をJSONファイルに永続化するキャッシュ"""

    def __init__(self, cache_path=DEFAULT_CACHE_PATH):
        self.cache_path = Path(cache_path)
        self._data = self._load()

    def _load(self):
        if not self.cache_path.exists():
            return {}
        with open(self.cache_path, encoding="utf-8") as f:
            return json.load(f)

    def save(self):
        self.cache_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.cache_path, "w", encoding="utf-8") as f:
            json.dump(self._data, f, ensure_ascii=False)

    def __contains__(self, address):
        return address in self._data

    def get(self, address):
        """キャッシュ済みなら(lon,lat)、無ければNoneを返す"""
        entry = self._data.get(address)
        return tuple(entry) if entry is not None else None

    def set(self, address, lon, lat):
        self._data[address] = [lon, lat]


def get_lat_lon(addresses, cache_path=DEFAULT_CACHE_PATH):

    cache = GeocodeCache(cache_path)

    # 同一建物の複数部屋で住所が重複するため、ユニークかつ未キャッシュの住所のみ問い合わせる
    addresses_to_fetch = sorted({a for a in addresses if a not in cache})

    if addresses_to_fetch:
        with Pool(processes=multiprocessing.cpu_count()) as pool:
            with tqdm(total=len(addresses_to_fetch)) as pbar:
                for address, (lon, lat) in zip(addresses_to_fetch, pool.imap(search_address, addresses_to_fetch)):
                    if lon is not None and lat is not None:
                        cache.set(address, lon, lat)
                    pbar.update(1)

        # 取得できなかった住所は次回再トライできるよう、キャッシュには書き込まない
        cache.save()

    lons=[(cache.get(address) or (None, None))[0] for address in addresses]
    lats=[(cache.get(address) or (None, None))[1] for address in addresses]

    return lons,lats
