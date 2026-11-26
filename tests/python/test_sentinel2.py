"""fetch-sentinel2, against small local scenes standing in for Sentinel-2's (no network)."""

import numpy as np
import rasterio
from conftest import E0, N0, UTM, square_route, write_gpx
from rasterio.transform import from_origin

from tools.coursebuilder.gpx import read_gpx
from tools.coursebuilder.sentinel2 import choose, credit_args, fetch


def scene(path, colour, east_edge=None):
    """A 3 km true-colour scene round the loop, one colour, black (no data) east of east_edge if given."""
    res, n = 10, 300
    west, north = E0 - 1500, N0 + 1500
    rgb = np.zeros((3, n, n), dtype="uint8")
    rgb[:] = np.array(colour, dtype="uint8")[:, None, None]
    if east_edge is not None:
        rgb[:, :, int((east_edge - west) / res) :] = 0
    profile = dict(driver="GTiff", width=n, height=n, count=3, dtype="uint8", crs=UTM, nodata=0)
    with rasterio.open(path, "w", transform=from_origin(west, north, res, res), **profile) as dst:
        dst.write(rgb)
    return str(path)


def feature(id, cloud, nodata=0, visual=True):
    assets = {"visual": {"href": f"https://example.org/{id}/TCI.tif"}} if visual else {}
    props = {"eo:cloud_cover": cloud, "s2:nodata_pixel_percentage": nodata, "datetime": "2025-07-01T16:00:00Z"}
    return {"id": id, "properties": props, "assets": assets}


def test_clearest_first_and_cloudy_left_out():
    found = [feature("a", 3.0), feature("b", 0.2, nodata=30), feature("c", 0.21), feature("d", 40), feature("e", 0)]
    found.append(feature("f", 0, visual=False))
    assert [f["id"] for f in choose(found, 5)] == ["e", "c", "b", "a"]  # b and c are as clear: the complete one first


def test_gaps_are_filled_from_the_next_scene(tmp_path):
    route = read_gpx(write_gpx(tmp_path / "route.gpx", square_route()))
    first = scene(tmp_path / "first.tif", (200, 40, 40), east_edge=E0)  # covers only the west half
    second = scene(tmp_path / "second.tif", (40, 200, 40))
    third = scene(tmp_path / "third.tif", (40, 40, 200))
    path, years = fetch(
        route, tmp_path / "out", 195, [2024, 2025], sources=[(first, 2025), (second, 2024), (third, 2023)],
        log=lambda *_: None,
    )  # fmt: skip
    assert years == [2024, 2025], "the third scene wasn't needed"
    with rasterio.open(path) as src:
        assert src.crs.to_epsg() == 32630
        rgb = src.read()
        n = src.width
    assert rgb[0, n // 2, : n // 4].mean() > 190, "west from the first scene (red)"
    assert rgb[1, n // 2, -n // 4 :].mean() > 190, "east from the second (green)"
    assert rgb.max(axis=0).min() > 0, "nothing left empty"


def test_credit_names_the_years():
    assert "Copernicus Sentinel data 2025." in credit_args([2025])[1]
    assert "Copernicus Sentinel data 2023–2025." in credit_args([2023, 2025])[1]
