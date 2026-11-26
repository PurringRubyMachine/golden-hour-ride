"""Building courses from synthetic DTMs, where the right answer is known."""

import hashlib
import json
import shlex
from pathlib import Path

import numpy as np
import pytest
from conftest import E0, N0, UTM, plane, square_route, write_dtm, write_gpx
from pyproj import Transformer

from tools.coursebuilder import BuildError
from tools.coursebuilder.build import build
from tools.coursebuilder.validate import validate_folder

# A 1400 m square of DTM around the loop, which with a 200 m margin needs a 1000 m terrain square.
WEST, NORTH, SPAN = E0 - 700, N0 + 700, 1400


def read_course(courses, id="test-loop"):
    folder = Path(courses) / id
    course = json.loads((folder / "course.json").read_text())
    road = json.loads((folder / "road.json").read_text())
    t = course["terrain"]
    q = np.frombuffer((folder / "terrain.bin").read_bytes(), dtype="<u2").reshape(t["cells"] + 1, t["cells"] + 1)
    terrain = t["min"] + q / 65535 * (t["max"] - t["min"])
    return course, road, terrain


def world(course, x, z):
    return course["origin"]["x"] + x, course["origin"]["y"] - z


def check_against_plane(course, road, terrain, road_tol, terrain_tol):
    errs = [abs(y - plane(*world(course, x, z))) for x, y, z in road]
    assert max(errs) < road_tol, f"road heights off the plane by up to {max(errs):.3f} m"
    t, half = course["terrain"], course["terrain"]["size"] / 2
    n = np.arange(t["cells"] + 1) * (t["size"] / t["cells"])
    e_grid, n_grid = np.meshgrid(course["origin"]["x"] - half + n, course["origin"]["y"] + half - n)
    diff = np.abs(terrain - plane(e_grid, n_grid))
    assert diff.max() < terrain_tol, f"terrain off the plane by up to {diff.max():.3f} m"


def test_tilted_plane(options):
    o = options()
    write_dtm(Path(o.dtm[0]) / "plane.tif", UTM, WEST, NORTH, 2, SPAN // 2, SPAN // 2)
    result = build(o, log=lambda *_: None)
    course, road, terrain = read_course(o.courses_dir)

    assert course["origin"]["crs"] == UTM  # the DTM's own system: projected, and true to scale here
    assert course["terrain"]["size"] == 1000 and course["terrain"]["cells"] == 100
    assert course["credits"] == [{"text": "Heights: a test plane", "licence": "CC0-1.0"}]
    assert "scenery" not in course  # plain, without OpenStreetMap
    # Straight sides are exact (see the grade below); the smoothing rounds off the square's corners a little.
    check_against_plane(course, road, terrain, road_tol=0.3, terrain_tol=0.01)

    # Along the south side, heading east, the road climbs at the plane's 3 %.
    h, line = result["heights"], result["line"]
    k = 30  # 150 m from the south-west corner
    grade = (h[k + 4] - h[k]) / (line[k + 4][0] - line[k][0])
    assert grade == pytest.approx(0.03, abs=1e-6)

    index = json.loads((Path(o.courses_dir) / "index.json").read_text())
    assert index == [{"id": "test-loop", "name": "Test loop", "lengthKm": 2.4, "climbM": 24}]
    assert validate_folder(Path(o.courses_dir) / "test-loop", index) == []


def test_hole_is_filled(options):
    o = options()
    hole = (E0 + 450, N0 + 450, E0 + 520, N0 + 520)  # 70 m across, outside the loop
    write_dtm(Path(o.dtm[0]) / "holey.tif", UTM, WEST, NORTH, 2, SPAN // 2, SPAN // 2, hole=hole)
    messages = []
    build(o, log=messages.append)
    course, road, terrain = read_course(o.courses_dir)
    assert any("filled" in m for m in messages)
    # Filled by interpolating from the edges: on a 3 % slope, within about a metre of the plane across a 70 m hole.
    check_against_plane(course, road, terrain, road_tol=0.3, terrain_tol=1.5)


def test_files_in_different_coordinate_systems(options, tmp_path):
    """The west half in latitude and longitude, the east half in UTM: mosaicked, and UTM chosen to work in."""
    o = options()
    # Geographic first: it can't be worked in (degrees), so the builder falls back to the route's UTM zone.
    write_dtm(Path(o.dtm[0]) / "a-west.tif", "EPSG:4326", -3.012, 51.465, 0.00002, 650, 1350)
    write_dtm(Path(o.dtm[0]) / "b-east.tif", UTM, E0 - 20, NORTH, 2, 370, SPAN // 2)
    build(o, log=lambda *_: None)
    course, road, terrain = read_course(o.courses_dir)
    assert course["origin"]["crs"] == UTM
    check_against_plane(course, road, terrain, road_tol=0.3, terrain_tol=0.1)


def test_finest_file_wins_where_files_overlap(options):
    o = options()
    write_dtm(
        Path(o.dtm[0]) / "coarse.tif",
        UTM,
        WEST,
        NORTH,
        10,
        SPAN // 10,
        SPAN // 10,
        height_at=lambda e, n: plane(e, n) + 50,
    )
    write_dtm(Path(o.dtm[0]) / "fine.tif", UTM, WEST, NORTH, 2, SPAN // 2, SPAN // 2)
    build(o, log=lambda *_: None)
    course, road, terrain = read_course(o.courses_dir)
    check_against_plane(course, road, terrain, road_tol=0.3, terrain_tol=0.01)


def test_dtm_that_misses_part_of_the_square(options):
    o = options()
    write_dtm(Path(o.dtm[0]) / "half.tif", UTM, WEST, NORTH, 2, 500, SPAN // 2)  # only the western 1000 m
    with pytest.raises(BuildError, match=r"has no DTM data: between latitude .* longitude"):
        build(o, log=lambda *_: None)


def test_dtm_somewhere_else(options):
    o = options()
    write_dtm(Path(o.dtm[0]) / "far.tif", UTM, WEST + 50_000, NORTH, 10, 140, 140)
    with pytest.raises(BuildError, match="don't cover"):
        build(o, log=lambda *_: None)


def test_open_route_is_refused_unless_closed(options, tmp_path):
    write_dtm(tmp_path / "dtm" / "plane.tif", UTM, WEST, NORTH, 2, SPAN // 2, SPAN // 2)
    open_route = write_gpx(tmp_path / "open.gpx", square_route()[:-20])  # stops 400 m short
    with pytest.raises(BuildError, match="--close"):
        build(options(route=str(open_route)), log=lambda *_: None)
    build(options(route=str(open_route), close=True), log=lambda *_: None)


def test_pastoral_options(options, tmp_path):
    lon, lat = Transformer.from_crs(UTM, "EPSG:4326", always_xy=True).transform(E0 + 100, N0 - 50)
    o = options(scenery_style="pastoral-1800s", smoke=[(lat, lon)], short_name="Test")
    write_dtm(Path(o.dtm[0]) / "plane.tif", UTM, WEST, NORTH, 2, SPAN // 2, SPAN // 2)
    build(o, log=lambda *_: None)
    course, _, _ = read_course(o.courses_dir)
    opts = course["scenery"]["options"]
    assert course["scenery"]["style"] == "pastoral-1800s" and "file" not in course["scenery"]
    assert opts["sheepAbove"] > opts["stooksBelow"] and opts["sheepAbove"] % 5 == 0
    assert opts["smoke"][0] == pytest.approx([100, 50], abs=0.1)  # local x east, z south
    assert course["shortName"] == "Test"


def test_rebuild_replaces_index_entry(options):
    o = options()
    write_dtm(Path(o.dtm[0]) / "plane.tif", UTM, WEST, NORTH, 2, SPAN // 2, SPAN // 2)
    index_path = Path(o.courses_dir) / "index.json"
    index_path.parent.mkdir()
    index_path.write_text('[{"id": "valley", "name": "The valley", "lengthKm": 3.3, "climbM": 70}]')
    build(o, log=lambda *_: None)
    build(options(name="Renamed"), log=lambda *_: None)
    index = json.loads(index_path.read_text())
    assert [e["id"] for e in index] == ["valley", "test-loop"]
    assert index[1]["name"] == "Renamed"


def test_build_json_records_the_sources(options, tmp_path, monkeypatch):
    write_dtm(tmp_path / "dtm" / "plane.tif", UTM, WEST, NORTH, 2, SPAN // 2, SPAN // 2)
    monkeypatch.chdir(tmp_path)  # paths in build.json are relative to here
    o = options(start=100, sheep_above=175.0, scenery_style="pastoral-1800s")
    build(o, log=lambda *_: None)
    folder = tmp_path / "courses" / "test-loop"
    info = json.loads((folder / "build.json").read_text())
    assert info["builtWith"] == "tools/coursebuilder"
    assert info["route"] == {
        "file": "route.gpx",
        "sha256": hashlib.sha256(Path(o.route).read_bytes()).hexdigest(),
        "kept": False,
    }
    assert info["dtm"] == {"workingCrs": "EPSG:32630", "files": ["plane.tif"]}
    assert "openStreetMap" not in info  # built without it
    cmd = shlex.split(info["command"])
    assert cmd[:4] == ["python", "-m", "tools.coursebuilder", "build"]
    assert cmd[cmd.index("--route") + 1] == "route.gpx"
    assert cmd[cmd.index("--dtm") + 1] == "dtm"
    assert cmd[cmd.index("--name") + 1] == "Test loop"
    assert cmd[cmd.index("--start") + 1] == "100" and cmd[cmd.index("--sheep-above") + 1] == "175"
    assert "--no-osm" in cmd and "--keep-route" not in cmd
    assert not (folder / "route.gpx").exists()


def test_paths_outside_the_working_folder_become_bare_names(options, tmp_path, monkeypatch):
    write_dtm(tmp_path / "dtm" / "plane.tif", UTM, WEST, NORTH, 2, SPAN // 2, SPAN // 2)
    (tmp_path / "elsewhere").mkdir()
    monkeypatch.chdir(tmp_path / "elsewhere")
    build(options(), log=lambda *_: None)
    info = json.loads((tmp_path / "courses" / "test-loop" / "build.json").read_text())
    cmd = shlex.split(info["command"])
    assert cmd[cmd.index("--route") + 1] == "route.gpx"
    assert str(tmp_path) not in info["command"]


def test_keep_route_copies_the_gpx_and_rebuilds_from_it(options, tmp_path, monkeypatch):
    write_dtm(tmp_path / "dtm" / "plane.tif", UTM, WEST, NORTH, 2, SPAN // 2, SPAN // 2)
    monkeypatch.chdir(tmp_path)
    o = options(keep_route=True)
    build(o, log=lambda *_: None)
    folder = tmp_path / "courses" / "test-loop"
    assert (folder / "route.gpx").read_bytes() == Path(o.route).read_bytes()
    info = json.loads((folder / "build.json").read_text())
    cmd = shlex.split(info["command"])
    assert cmd[cmd.index("--route") + 1] == "courses/test-loop/route.gpx" and "--keep-route" in cmd
    assert info["route"]["kept"] is True

    # rebuilding from the course's own copy, with or without --keep-route, keeps it
    build(options(route=str(folder / "route.gpx")), log=lambda *_: None)
    assert (folder / "route.gpx").exists()
    assert json.loads((folder / "build.json").read_text())["route"]["kept"] is True

    # rebuilding from another GPX without --keep-route removes the old copy
    build(options(), log=lambda *_: None)
    assert not (folder / "route.gpx").exists()


def test_sparse_gpx_gets_a_warning(options, tmp_path):
    write_dtm(tmp_path / "dtm" / "plane.tif", UTM, WEST, NORTH, 2, SPAN // 2, SPAN // 2)
    sparse = write_gpx(tmp_path / "turns.gpx", square_route(step=300))  # a point every 300 m: corners and middles
    logged = []
    build(options(route=str(sparse)), log=logged.append)
    assert any(line.startswith("warning: the GPX's points are") for line in logged)
    logged.clear()
    build(options(), log=logged.append)
    assert not any(line.startswith("warning") for line in logged)
