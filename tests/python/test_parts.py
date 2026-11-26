"""The builder's parts: GPX, route cleaning, coordinate systems, OpenStreetMap conversion, JSON layout."""

import base64
import json
import math
from pathlib import Path

import pytest
from conftest import UTM, square_route, write_gpx
from pyproj import CRS, Transformer

from tools.coursebuilder import BuildError
from tools.coursebuilder.__main__ import _metres
from tools.coursebuilder.course import dumps
from tools.coursebuilder.frame import Frame, choose_crs, crs_name
from tools.coursebuilder.gpx import read_gpx
from tools.coursebuilder.osm import convert
from tools.coursebuilder.road import across_bridges, climb, smooth, steepest
from tools.coursebuilder.route import STEP, make_loop, remove_spurs

ROOT = Path(__file__).resolve().parents[2]


# --- GPX


def test_gpx_track_or_route(tmp_path):
    pts = square_route()
    track = read_gpx(write_gpx(tmp_path / "t.gpx", pts, "trk"))
    route = read_gpx(write_gpx(tmp_path / "r.gpx", pts, "rte"))
    assert len(track) == len(route) == len(pts)
    assert track == route


def test_gpx_without_points(tmp_path):
    (tmp_path / "empty.gpx").write_text('<gpx xmlns="http://www.topografix.com/GPX/1/1"><wpt lat="1" lon="2"/></gpx>')
    with pytest.raises(BuildError, match="no track or route"):
        read_gpx(tmp_path / "empty.gpx")
    (tmp_path / "bad.gpx").write_text("<gpx><trk>")
    with pytest.raises(BuildError, match="could not read"):
        read_gpx(tmp_path / "bad.gpx")


# --- route


def test_spur_is_removed():
    # east along a road, a 100 m detour north and back, then on east
    there = [(x, 0.0) for x in range(0, 200, 5)]
    spur = [(200.0, y) for y in range(0, 100, 5)] + [(200.0, y) for y in range(100, -1, -5)]
    on = [(x, 0.0) for x in range(205, 400, 5)]
    cleaned = remove_spurs(there + spur + on)
    assert max(y for _, y in cleaned) == 0


def test_loop_is_evenly_spaced_and_closed():
    line, gap = make_loop(square_route(side=600, step=37))
    assert gap < 1
    gaps = [math.dist(a, b) for a, b in zip(line, line[1:] + line[:1])]
    assert max(gaps) <= STEP + 1e-6 and len(line) == pytest.approx(2400 / STEP, abs=1)


def test_open_route():
    pts = square_route()[:-20]
    with pytest.raises(BuildError, match="400 m apart"):
        make_loop(pts)
    line, gap = make_loop(pts, close=True)
    assert gap == pytest.approx(400, abs=1)
    assert len(line) == pytest.approx(2400 / STEP, abs=1)


# --- road heights


def test_smoothing_wraps_round_the_loop():
    h = [10.0] * 100
    h[0] = 30.0  # a spike at the join
    s = smooth(h)
    assert max(s) == pytest.approx(10.0)  # the median removes it, even at the start of the list
    ramp = [math.sin(2 * math.pi * k / 100) * 20 for k in range(100)]
    assert climb(ramp) == pytest.approx(40, abs=0.5)
    up, down = steepest(ramp, 5)
    assert up == pytest.approx(-down, abs=0.01)


# --- coordinate systems


@pytest.mark.parametrize(
    "dtm, lon, lat, expect",
    [
        ("EPSG:27700", -2.07, 51.87, "EPSG:27700"),  # British National Grid at Cheltenham: true to scale, kept
        ("EPSG:4326", -2.07, 51.87, "EPSG:32630"),  # degrees: UTM instead
        ("EPSG:3979", -75.7, 45.4, "EPSG:32618"),  # Canada Atlas Lambert at Ottawa stretches 0.5 %: UTM instead
        ("EPSG:2950", -73.6, 45.5, "EPSG:2950"),  # Quebec MTM zone 8 at Montreal: kept
        ("EPSG:2193", 172.6, -43.5, "EPSG:2193"),  # New Zealand Transverse Mercator at Christchurch: kept
        (None, 7.4, 46.9, "EPSG:32632"),  # no system given: UTM
    ],
)
def test_working_crs(dtm, lon, lat, expect):
    assert crs_name(choose_crs(dtm and CRS.from_user_input(dtm), lon, lat)) == expect


def test_compound_crs_uses_its_horizontal_part():
    compound = CRS.from_user_input("EPSG:27700+5701")  # British National Grid + Newlyn heights
    assert crs_name(choose_crs(compound, -2.07, 51.87)) == "EPSG:27700"


# --- OpenStreetMap


def _square(lon0, lat0, d):
    return [{"lat": lat0 + dy, "lon": lon0 + dx} for dx, dy in ((0, 0), (d, 0), (d, d), (0, d), (0, 0))]


def test_osm_conversion():
    frame = Frame(CRS.from_user_input(UTM), 500_000, 5_700_000, 1000)
    to_ll = Transformer.from_crs(UTM, "EPSG:4326", always_xy=True)
    lon0, lat0 = to_ll.transform(500_000, 5_700_000)  # the square's centre
    road = [(x, 0.0) for x in range(-500, 501, 10)]  # local: a road east-west through the middle
    near = lat0 - 0.0003  # about 33 m south of the road (local z positive is south)
    elements = [
        {"type": "way", "tags": {"building": "house"}, "geometry": _square(lon0, near, 0.0001)},
        {"type": "way", "tags": {"building": "church"}, "geometry": _square(lon0 + 0.001, near, 0.0002)},
        {"type": "way", "tags": {"building": "house"}, "geometry": _square(lon0, lat0 - 0.00004, 0.00008)},  # on it
        {"type": "node", "tags": {"natural": "tree"}, "lat": near, "lon": lon0},
        {"type": "node", "tags": {"natural": "tree"}, "lat": lat0, "lon": lon0},  # in the road
        {"type": "way", "tags": {"barrier": "hedge"}, "geometry": [{"lat": near, "lon": lon0 - 0.001},
                                                                    {"lat": near, "lon": lon0 + 0.001}]},
        {"type": "way", "tags": {"natural": "wood"}, "geometry": _square(lon0 - 0.003, lat0 + 0.001, 0.002)},
    ]  # fmt: skip
    sc = convert(elements, frame, road)
    assert len(sc["buildings"]) == 2  # the one on the road is left out
    house, church = sorted(sc["buildings"], key=lambda b: b[5])
    assert house[5] == 5.6 and house[6] == 1 and church[5] == 13.0
    assert house[1] == pytest.approx(28, abs=3)  # local z: south of the road
    assert len(sc["trees"]) == 1
    assert len(sc["lines"]) >= 20 and all(line[4] == 0 for line in sc["lines"])  # ~140 m of hedge in 6 m pieces
    bits = base64.b64decode(sc["woods"])
    woods = sum(bin(b).count("1") for b in bits)
    assert woods == pytest.approx(140 * 220 / 100, rel=0.25)  # a wood about 140 m × 220 m, one bit per 10 m cell
    assert len(bits) == math.ceil(101**2 / 8)


# --- JSON layout


@pytest.mark.parametrize("name", ["leckhampton/course.json", "valley/course.json", "index.json"])
def test_json_layout_matches_the_repository(name):
    """course.json and index.json come out laid out as Prettier leaves them, so the format check passes."""
    text = (ROOT / "courses" / name).read_text(encoding="utf-8")
    assert dumps(json.loads(text)) + "\n" == text


def test_whole_metres_stay_whole():
    assert _metres("850") == 850 and isinstance(_metres("850"), int)
    assert _metres("850.0") == 850 and isinstance(_metres("850.0"), int)
    assert _metres("12.5") == 12.5


def rectangle_loop(w=1000, h=200, step=5):
    """A loop round a rectangle, anticlockwise from the south-west corner, a point every `step` metres."""
    pts = [(x, 0.0) for x in range(0, w, step)] + [(float(w), y) for y in range(0, h, step)]
    pts += [(x, float(h)) for x in range(w, 0, -step)] + [(0.0, y) for y in range(h, 0, -step)]
    return [(float(x), float(y)) for x, y in pts]


def test_road_is_drawn_straight_across_a_bridge():
    line = rectangle_loop()
    # a valley under the road at x 490-530 on the south side: the bare-ground DTM dips 4 m there
    heights = [100.0 - (4.0 if y == 0 and 490 <= x <= 530 else 0.0) for x, y in line]
    out, crossed = across_bridges(line, heights, [[(485.0, 2.0), (535.0, 2.0)]])
    assert crossed == 1
    assert max(abs(h - 100.0) for h in out) < 1e-9


def test_road_under_a_bridge_or_beside_one_is_left_alone():
    line = rectangle_loop()
    heights = [100.0 + 0.01 * x for x, _ in line]
    across = [[(300.0, -20.0), (300.0, 20.0)]]  # another road crossing over ours
    beside = [[(600.0, 15.0), (700.0, 15.0)]]  # a bridge on a road 15 m away
    out, crossed = across_bridges(line, heights, across + beside)
    assert crossed == 0 and out == heights


def test_bridge_across_the_start_of_the_loop():
    line = rectangle_loop()
    k = line.index((500.0, 0.0))
    line = line[k:] + line[:k]  # the loop starts and ends at x 500, in the middle of the bridge
    heights = [100.0 - (3.0 if y == 0 and 490 <= x <= 510 else 0.0) for x, y in line]
    out, crossed = across_bridges(line, heights, [[(480.0, 0.0), (520.0, 0.0)]])
    assert crossed == 1
    assert max(abs(h - 100.0) for h in out) < 1e-9
