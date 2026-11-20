"""物件からの眺め(一人称視点)を作るためのロジック。

`extract/osm.py`が返すOverpass APIのJSONを、描画しやすい形(建物の多角形と高さ、
道路の線など)に加工する。描画そのもの(deck.gl)は`analysis/view_html.py`が担う。

OSMの建物には高さ(height)や階数(building:levels)のタグが付いていないものが多い
(特に日本は基盤地図情報由来の輪郭だけの建物が多い)ため、タグが無い建物は
`default_height`の高さとして扱い、`estimated=True`の印を付けておく。
"""

import math
import re

# 1フロアあたりの高さの目安[m]
FLOOR_HEIGHT_M = 3.0
# 床から目線までの高さ[m]
EYE_LEVEL_M = 1.5

# 道路種別ごとの描画幅[m](実際の幅員ではなく見た目の目安)
ROAD_WIDTHS_M = {
    "motorway": 16,
    "trunk": 14,
    "primary": 12,
    "secondary": 10,
    "tertiary": 8,
    "motorway_link": 8,
    "trunk_link": 8,
    "primary_link": 8,
    "secondary_link": 7,
    "tertiary_link": 6,
    "residential": 6,
    "unclassified": 6,
    "living_street": 5,
    "service": 4,
    "pedestrian": 4,
    "track": 3,
    "footway": 2,
    "path": 2,
    "cycleway": 2,
    "steps": 2,
}
DEFAULT_ROAD_WIDTH_M = 4

# 「向き」の表記 -> 方位角(北=0, 時計回り)
_DIRECTION_BEARINGS = {
    "北": 0,
    "北北東": 22.5,
    "北東": 45,
    "東北東": 67.5,
    "東": 90,
    "東南東": 112.5,
    "南東": 135,
    "南南東": 157.5,
    "南": 180,
    "南南西": 202.5,
    "南西": 225,
    "西南西": 247.5,
    "西": 270,
    "西北西": 292.5,
    "北西": 315,
    "北北西": 337.5,
}

_GREEN_LEISURE = {"park", "garden", "pitch", "playground"}
_GREEN_LANDUSE = {"grass", "forest", "recreation_ground", "cemetery", "meadow"}
_GREEN_NATURAL = {"wood", "grassland", "scrub"}
_RAILWAYS = {"rail", "subway", "light_rail", "monorail", "tram"}


def parse_floor(value):
    """「5階」「12」「B1階」などから階数(int)を取り出す。取り出せなければNone。

    地下階(B1など)は眺めの対象外なので1階扱いにする。
    """
    if value is None:
        return None
    if isinstance(value, float) and math.isnan(value):
        return None
    text = str(value)
    match = re.search(r"\d+", text)
    if match is None:
        return None
    if re.match(r"\s*(B|Ｂ|地下)", text):
        return 1
    return max(1, int(match.group()))


def eye_height(floor, floor_height=FLOOR_HEIGHT_M, eye_level=EYE_LEVEL_M):
    """n階に立ったときの目線の高さ[m]。1階の床を地面(0m)とする。"""
    return (max(1, floor) - 1) * floor_height + eye_level


def bearing_from_direction(direction, default=180.0):
    """「南東」「南向き」のような向きの表記を方位角(北=0, 時計回り)に変換する。"""
    if not isinstance(direction, str):
        return default
    text = direction.strip().replace("向き", "")
    return float(_DIRECTION_BEARINGS.get(text, default))


def parse_height(value):
    """OSMのheight系タグ("12", "12 m", "12.5m")をメートル(float)に変換する。

    フィート表記(12')などメートル以外と判断できるものはNoneを返す。
    """
    if value is None:
        return None
    text = str(value).strip().lower()
    if "'" in text or "ft" in text or '"' in text:
        return None
    match = re.match(r"^(-?\d+(?:\.\d+)?)\s*(m)?$", text.replace(",", "."))
    if match is None:
        return None
    return float(match.group(1))


def _parse_levels(value):
    if value is None:
        return None
    match = re.match(r"^\s*(\d+(?:\.\d+)?)", str(value))
    if match is None:
        return None
    return float(match.group(1))


def estimate_building_height(tags, default_height):
    """建物タグから(下端の高さ, 上端の高さ, 推定値かどうか)を返す。

    優先順位: height > building:levels(+roof:levels) × 1フロアの高さ > default_height
    下端はmin_height > building:min_level × 1フロアの高さ > 0。
    """
    base = parse_height(tags.get("min_height"))
    if base is None:
        min_level = _parse_levels(tags.get("building:min_level"))
        base = min_level * FLOOR_HEIGHT_M if min_level is not None else 0.0

    top = parse_height(tags.get("height"))
    estimated = False
    if top is None:
        levels = _parse_levels(tags.get("building:levels"))
        if levels is not None:
            roof_levels = _parse_levels(tags.get("roof:levels")) or 0.0
            top = (levels + roof_levels) * FLOOR_HEIGHT_M
        else:
            top = default_height
            estimated = True

    # 屋根だけの建物などでbaseがtopを超えるおかしなデータを潰しておく
    top = max(top, base + 1.0)
    return base, top, estimated


def classify(tags):
    """OSMのタグから描画上の種別(building/road/rail/water/green)を判定する。"""
    if "building" in tags or "building:part" in tags:
        return "building"
    if "highway" in tags:
        return "road"
    if tags.get("railway") in _RAILWAYS:
        return "rail"
    if tags.get("natural") == "water" or tags.get("waterway") == "riverbank":
        return "water"
    if (
        tags.get("leisure") in _GREEN_LEISURE
        or tags.get("landuse") in _GREEN_LANDUSE
        or tags.get("natural") in _GREEN_NATURAL
    ):
        return "green"
    return None


def _coords(geometry):
    return [[node["lon"], node["lat"]] for node in geometry if node is not None]


def _is_closed(ring):
    return len(ring) >= 4 and ring[0] == ring[-1]


def _stitch_rings(segments):
    """マルチポリゴンのメンバーwayをつなぎ合わせて閉じたリングの一覧にする。

    OSMのマルチポリゴンは、外周が複数のwayに分割されていることがあるため、
    端点が一致するものを順につないでいく。閉じられなかったものは捨てる。
    """
    remaining = [list(s) for s in segments if len(s) >= 2]
    rings = []
    while remaining:
        ring = remaining.pop(0)
        changed = True
        while not _is_closed(ring) and changed:
            changed = False
            for i, seg in enumerate(remaining):
                if seg[0] == ring[-1]:
                    ring = ring + seg[1:]
                elif seg[-1] == ring[-1]:
                    ring = ring + seg[::-1][1:]
                elif seg[-1] == ring[0]:
                    ring = seg + ring[1:]
                elif seg[0] == ring[0]:
                    ring = seg[::-1] + ring[1:]
                else:
                    continue
                remaining.pop(i)
                changed = True
                break
        if _is_closed(ring):
            rings.append(ring)
    return rings


def _element_polygons(element):
    """way/relationから多角形のリスト(各要素は[外周, 穴...]のリング配列)を作る。"""
    if element["type"] == "way":
        ring = _coords(element.get("geometry", []))
        return [[ring]] if _is_closed(ring) else []

    if element["type"] == "relation":
        members = [m for m in element.get("members", []) if m.get("type") == "way" and m.get("geometry")]
        outers = _stitch_rings([_coords(m["geometry"]) for m in members if m.get("role", "outer") in ("outer", "")])
        inners = _stitch_rings([_coords(m["geometry"]) for m in members if m.get("role") == "inner"])
        if len(outers) == 1:
            return [[outers[0], *inners]]
        # 外周が複数ある場合はどの穴がどの外周に属するかの判定を省略し、穴は無視する
        return [[outer] for outer in outers]

    return []


def point_in_ring(lon, lat, ring):
    """(lon, lat)がリングの内側にあるか(レイキャスティング法)。"""
    inside = False
    n = len(ring)
    for i in range(n):
        x1, y1 = ring[i]
        x2, y2 = ring[(i + 1) % n]
        if (y1 > lat) != (y2 > lat):
            x_cross = x1 + (lat - y1) * (x2 - x1) / (y2 - y1)
            if lon < x_cross:
                inside = not inside
    return inside


def build_scene(overpass_json, default_height=FLOOR_HEIGHT_M * 2):
    """Overpass APIのJSONを描画用のシーン(dict)に変換する。

    戻り値:
        {
          "buildings": [{"polygon": [[lon, lat], ...] or [[外周], [穴]...],
                          "base": float, "height": float, "estimated": bool,
                          "name": str, "levels": str}],
          "roads": [{"path": [[lon, lat], ...], "width": float, "name": str}],
          "rails": [{"path": [[lon, lat], ...], "name": str}],
          "water": [{"polygon": ...}],
          "green": [{"polygon": ...}],
        }
    """
    scene = {"buildings": [], "roads": [], "rails": [], "water": [], "green": []}

    for element in overpass_json.get("elements", []):
        tags = element.get("tags", {})
        kind = classify(tags)
        if kind is None:
            continue

        if kind in ("road", "rail"):
            if element["type"] != "way":
                continue
            path = _coords(element.get("geometry", []))
            if len(path) < 2:
                continue
            item = {"path": path, "name": tags.get("name", "")}
            if kind == "road":
                item["width"] = ROAD_WIDTHS_M.get(tags["highway"], DEFAULT_ROAD_WIDTH_M)
                scene["roads"].append(item)
            else:
                scene["rails"].append(item)
            continue

        for rings in _element_polygons(element):
            polygon = rings[0] if len(rings) == 1 else rings
            if kind == "building":
                base, top, estimated = estimate_building_height(tags, default_height)
                scene["buildings"].append({
                    "polygon": polygon,
                    "base": base,
                    "height": top,
                    "estimated": estimated,
                    "name": tags.get("name", ""),
                    "levels": tags.get("building:levels", ""),
                })
            else:
                scene[kind].append({"polygon": polygon})

    return scene


def _outer_ring(polygon):
    # [[lon, lat], ...] と [[[lon, lat], ...], [穴]...] の両方に対応する
    return polygon[0] if isinstance(polygon[0][0], list) else polygon


def remove_buildings_at(scene, lon, lat):
    """(lon, lat)を含む建物(=物件自身の建物)を取り除いたシーンと、取り除いた建物を返す。

    物件の建物が残っていると、カメラが建物の壁の内側に入って何も見えなくなるため。
    """
    kept, removed = [], []
    for building in scene["buildings"]:
        if point_in_ring(lon, lat, _outer_ring(building["polygon"])):
            removed.append(building)
        else:
            kept.append(building)
    return {**scene, "buildings": kept}, removed


def offset_lonlat(lon, lat, distance_m, bearing_deg):
    """(lon, lat)からbearing_deg方向にdistance_m[m]進んだ地点の(lon, lat)を返す(近距離用の近似)。"""
    rad = math.radians(bearing_deg)
    dlat = distance_m * math.cos(rad) / 111_320
    dlon = distance_m * math.sin(rad) / (111_320 * math.cos(math.radians(lat)))
    return lon + dlon, lat + dlat
