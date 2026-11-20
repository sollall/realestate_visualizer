"""OpenStreetMap(Overpass API)から物件周辺の建物・道路などを取得するIF層。

Overpass APIはOSMのデータを範囲・タグ指定で取り出せる公開API。
ここでは`out geom;`で各wayの座標をまとめて返してもらい、加工は
`analysis/osm_view.py`側に任せる(ここはAPIへのアクセスだけを担う)。
"""

import requests
from retry import retry

OVERPASS_URL = "https://overpass-api.de/api/interpreter"

# Overpass APIの利用ポリシーに従い、アクセス元が分かるUser-Agentを付ける
USER_AGENT = "realestate_visualizer (OSM view page)"


def build_overpass_query(lat, lon, radius_m):
    """(lat, lon)から半径radius_m[m]以内の建物・道路・鉄道・水域・緑地を取るクエリを組み立てる。"""
    around = f"(around:{int(radius_m)},{lat},{lon})"
    return f"""
[out:json][timeout:90];
(
  way["building"]{around};
  relation["building"]{around};
  way["building:part"]{around};
  way["highway"]["highway"!~"proposed|construction|platform|elevator|bus_stop"]{around};
  way["railway"~"^(rail|subway|light_rail|monorail|tram)$"]{around};
  way["natural"="water"]{around};
  relation["natural"="water"]{around};
  way["waterway"="riverbank"]{around};
  way["leisure"~"^(park|garden|pitch|playground)$"]{around};
  way["landuse"~"^(grass|forest|recreation_ground|cemetery|meadow)$"]{around};
  way["natural"~"^(wood|grassland|scrub)$"]{around};
);
out geom;
"""


@retry(tries=3, delay=5, backoff=2)
def fetch_osm_features(lat, lon, radius_m):
    """Overpass APIを叩き、レスポンスのJSON(dict)をそのまま返す。"""
    query = build_overpass_query(lat, lon, radius_m)
    response = requests.post(
        OVERPASS_URL,
        data={"data": query},
        headers={"User-Agent": USER_AGENT},
        timeout=120,
    )
    response.raise_for_status()
    return response.json()
