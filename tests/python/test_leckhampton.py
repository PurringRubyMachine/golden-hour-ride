"""Acceptance test: rebuild Leckhampton from Environment Agency data and compare it with the course in the repository.

Needs the network the first time (about 50 MB of LiDAR tiles, kept in tools/.cache/), so it only runs when asked:

    COURSEBUILDER_NETWORK=1 .venv/bin/pytest tests/python/test_leckhampton.py

OpenStreetMap scenery is left out: it changes as the map is edited, so it can't be compared.
"""

import json
import math
import os
from pathlib import Path

import pytest
from pyproj import Transformer

from tools.coursebuilder import ea
from tools.coursebuilder.build import Options, build
from tools.coursebuilder.gpx import read_gpx

ROOT = Path(__file__).resolve().parents[2]
CACHE = ROOT / "tools" / ".cache"

pytestmark = pytest.mark.skipif(
    os.environ.get("COURSEBUILDER_NETWORK") != "1", reason="set COURSEBUILDER_NETWORK=1 to fetch LiDAR and run this"
)


def course_points(folder):
    """A course's road points in its own coordinate system: [(x, y, height), ...]."""
    course = json.loads((folder / "course.json").read_text())
    road = json.loads((folder / "road.json").read_text())
    ox, oy = course["origin"]["x"], course["origin"]["y"]
    return course, [(ox + x, oy - z, h) for x, h, z in road]


def write_gpx(path, course, points):
    to_ll = Transformer.from_crs(course["origin"]["crs"], "EPSG:4326", always_xy=True)
    pts = [to_ll.transform(x, y) for x, y, _ in points]
    pts.append(pts[0])
    body = "".join(f'<trkpt lat="{lat:.7f}" lon="{lon:.7f}"/>' for lon, lat in pts)
    path.write_text(
        f'<gpx version="1.1" xmlns="http://www.topografix.com/GPX/1/1"><trk><trkseg>{body}</trkseg></trk></gpx>'
    )


def climb(heights):
    return sum(max(0.0, b - a) for a, b in zip(heights, heights[1:] + heights[:1]))


def test_rebuild_leckhampton(tmp_path):
    course, old = course_points(ROOT / "courses" / "leckhampton")
    gpx = tmp_path / "leckhampton.gpx"
    write_gpx(gpx, course, old)
    tiles = CACHE / "ea-leckhampton"
    ea.fetch(read_gpx(gpx), tiles, margin=1300)
    credit = dict(zip(ea.CREDIT_ARGS[::2], ea.CREDIT_ARGS[1::2]))
    build(
        Options(
            id="leckhampton",
            name="Leckhampton Hill loop",
            route=str(gpx),
            dtm=[str(tiles)],
            heights_credit=credit["--heights-credit"],
            heights_licence=credit["--heights-licence"],
            heights_url=credit["--heights-url"],
            start=850,
            osm=False,
            courses_dir=str(tmp_path / "courses"),
            cache_dir=str(CACHE),
        )
    )
    rebuilt_course, new = course_points(tmp_path / "courses" / "leckhampton")
    assert rebuilt_course["origin"]["crs"] == course["origin"]["crs"] == "EPSG:27700"

    # Compare each old road point with the nearest rebuilt one.
    diffs = []
    for x, y, h in old:
        nearest = min(new, key=lambda p: (p[0] - x) ** 2 + (p[1] - y) ** 2)
        assert math.dist(nearest[:2], (x, y)) < 10, "the rebuilt road should follow the same line"
        diffs.append(nearest[2] - h)
    mean_abs = sum(map(abs, diffs)) / len(diffs)
    old_climb, new_climb = climb([p[2] for p in old]), climb([p[2] for p in new])
    print(f"road heights: mean difference {mean_abs:.2f} m, largest {max(map(abs, diffs)):.2f} m")
    print(f"climbing: {old_climb:.0f} m before, {new_climb:.0f} m rebuilt")
    assert mean_abs < 0.5
    assert new_climb == pytest.approx(old_climb, rel=0.03)
