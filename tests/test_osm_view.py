"""analysis/osm_view.py・analysis/view_html.py・extract/osm.pyのテスト。
実際のOverpass APIへのアクセスは行わない。
"""

import json
import re

import pytest

import extract.osm as osm
from analysis.osm_view import (
    bearing_from_direction,
    build_scene,
    estimate_building_height,
    eye_height,
    offset_lonlat,
    parse_floor,
    parse_height,
    point_in_ring,
    remove_buildings_at,
)
from analysis.view_html import build_view_html


def square(lon, lat, d=0.001):
    return [
        {"lon": lon - d, "lat": lat - d},
        {"lon": lon + d, "lat": lat - d},
        {"lon": lon + d, "lat": lat + d},
        {"lon": lon - d, "lat": lat + d},
        {"lon": lon - d, "lat": lat - d},
    ]


@pytest.mark.parametrize("value, expected", [
    ("5階", 5), ("12", 12), (3.0, 3), ("B1階", 1), ("地下2階", 1), (None, None), (float("nan"), None), ("不明", None),
])
def test_parse_floor(value, expected):
    assert parse_floor(value) == expected


def test_eye_height():
    assert eye_height(1) == pytest.approx(1.5)
    assert eye_height(10) == pytest.approx(28.5)


@pytest.mark.parametrize("value, expected", [
    ("南東", 135), ("南向き", 180), ("北", 0), ("西北西", 292.5), (None, 180), ("不明", 180),
])
def test_bearing_from_direction(value, expected):
    assert bearing_from_direction(value) == expected


@pytest.mark.parametrize("value, expected", [
    ("12", 12.0), ("12 m", 12.0), ("12.5m", 12.5), ("40'", None), ("abc", None), (None, None),
])
def test_parse_height(value, expected):
    assert parse_height(value) == expected


def test_estimate_building_height_priority():
    # heightタグが最優先
    assert estimate_building_height({"height": "30", "building:levels": "3"}, 6) == (0.0, 30.0, False)
    # 次に階数(屋根階も足す)
    assert estimate_building_height({"building:levels": "4", "roof:levels": "1"}, 6) == (0.0, 15.0, False)
    # どちらも無ければ既定値で、推定扱い
    assert estimate_building_height({"building": "yes"}, 6) == (0.0, 6, True)
    # 下端の高さ(ピロティや渡り廊下など)
    assert estimate_building_height({"min_height": "10", "height": "20"}, 6) == (10.0, 20.0, False)
    assert estimate_building_height({"building:min_level": "2", "building:levels": "5"}, 6) == (6.0, 15.0, False)


def test_build_scene_classifies_elements():
    overpass_json = {"elements": [
        {"type": "way", "id": 1, "tags": {"building": "yes", "height": "20", "name": "ビル"},
         "geometry": square(139.0, 35.0)},
        {"type": "way", "id": 2, "tags": {"highway": "primary"},
         "geometry": [{"lon": 139.0, "lat": 35.0}, {"lon": 139.01, "lat": 35.0}]},
        {"type": "way", "id": 3, "tags": {"railway": "rail"},
         "geometry": [{"lon": 139.0, "lat": 35.01}, {"lon": 139.01, "lat": 35.01}]},
        {"type": "way", "id": 4, "tags": {"leisure": "park"}, "geometry": square(139.02, 35.0)},
        {"type": "way", "id": 5, "tags": {"natural": "water"}, "geometry": square(139.03, 35.0)},
        # 閉じていない建物や対象外のタグは無視する
        {"type": "way", "id": 6, "tags": {"building": "yes"}, "geometry": square(139.0, 35.0)[:3]},
        {"type": "way", "id": 7, "tags": {"amenity": "bench"}, "geometry": square(139.0, 35.0)},
        {"type": "node", "id": 8, "tags": {"building": "yes"}, "lat": 35.0, "lon": 139.0},
    ]}
    scene = build_scene(overpass_json, default_height=6)

    assert len(scene["buildings"]) == 1
    assert scene["buildings"][0]["height"] == 20.0
    assert scene["buildings"][0]["name"] == "ビル"
    assert len(scene["roads"]) == 1 and scene["roads"][0]["width"] == 12
    assert len(scene["rails"]) == 1
    assert len(scene["green"]) == 1
    assert len(scene["water"]) == 1


def test_build_scene_stitches_multipolygon_relation():
    """外周が2本のwayに分かれたマルチポリゴンも1つの多角形としてつなぐ"""
    ring = square(139.0, 35.0)
    relation = {
        "type": "relation", "id": 10, "tags": {"natural": "water", "type": "multipolygon"},
        "members": [
            {"type": "way", "role": "outer", "geometry": ring[:3]},
            # 向きが逆になっているwayも反転してつなげる
            {"type": "way", "role": "outer", "geometry": ring[2:][::-1]},
            {"type": "way", "role": "inner", "geometry": square(139.0, 35.0, d=0.0002)},
        ],
    }
    scene = build_scene({"elements": [relation]})

    assert len(scene["water"]) == 1
    outer, inner = scene["water"][0]["polygon"]
    assert outer[0] == outer[-1] and len(outer) == 5
    assert len(inner) == 5


def test_point_in_ring():
    ring = [[0, 0], [1, 0], [1, 1], [0, 1], [0, 0]]
    assert point_in_ring(0.5, 0.5, ring)
    assert not point_in_ring(1.5, 0.5, ring)


def test_remove_buildings_at_removes_only_the_listing_building():
    overpass_json = {"elements": [
        {"type": "way", "id": 1, "tags": {"building": "yes"}, "geometry": square(139.0, 35.0)},
        {"type": "way", "id": 2, "tags": {"building": "yes"}, "geometry": square(139.01, 35.0)},
    ]}
    scene = build_scene(overpass_json)
    kept, removed = remove_buildings_at(scene, 139.0, 35.0)

    assert len(removed) == 1
    assert len(kept["buildings"]) == 1
    assert kept["buildings"][0]["polygon"][0][0] == pytest.approx(139.01 - 0.001)


def test_offset_lonlat_moves_roughly_by_distance():
    lon, lat = offset_lonlat(139.0, 35.0, 1000, 0)
    assert lon == pytest.approx(139.0)
    assert (lat - 35.0) * 111_320 == pytest.approx(1000)
    lon, lat = offset_lonlat(139.0, 35.0, 1000, 90)
    assert lat == pytest.approx(35.0)
    assert lon > 139.0


def test_build_view_html_embeds_config_safely():
    scene = {"buildings": [{"polygon": [[0, 0], [1, 0], [1, 1], [0, 0]], "base": 0, "height": 10,
                            "estimated": False, "name": "</script><b>x</b>", "levels": ""}],
             "roads": [], "rails": [], "water": [], "green": []}
    html = build_view_html(scene, lon=139.0, lat=35.0, eye_height=28.5, bearing=135, pitch=-5,
                           ground_polygon=[[0, 0], [1, 0], [1, 1]], title="<テスト>")

    # 外部入力由来の"</script>"でscriptタグが途中で閉じないこと
    assert html.count("</script>") == 2
    config = json.loads(re.search(r"const config = (.*);\n", html).group(1).replace("<\\/", "</"))
    assert config["eyeHeight"] == 28.5
    assert config["bearing"] == 135
    assert config["title"] == "&lt;テスト&gt;"
    assert "FirstPersonView" in html


def test_fetch_osm_features_posts_query(monkeypatch):
    captured = {}

    class FakeResponse:
        def raise_for_status(self):
            pass

        def json(self):
            return {"elements": []}

    def fake_post(url, data, headers, timeout):
        captured["url"] = url
        captured["query"] = data["data"]
        return FakeResponse()

    monkeypatch.setattr(osm.requests, "post", fake_post)
    assert osm.fetch_osm_features(35.0, 139.0, 500) == {"elements": []}
    assert captured["url"] == osm.OVERPASS_URL
    assert "(around:500,35.0,139.0)" in captured["query"]
    assert "out geom;" in captured["query"]
