"""fetch-hrdem, against two small local mosaics standing in for HRDEM's (no network)."""

import math

import numpy as np
import pytest
import rasterio
from pyproj import Transformer
from rasterio.transform import from_origin

from tools.coursebuilder.frame import square_around, utm_for
from tools.coursebuilder.hrdem import COARSE, FINE, LAMBERT, NODATA, TILE, fetch, square_in_lambert, tiles_for
from tools.coursebuilder.route import make_loop

LON, LAT = -75.76, 45.44  # near the start of the Gatineau Park Loop
X0, Y0 = Transformer.from_crs("EPSG:4326", LAMBERT, always_xy=True).transform(LON, LAT)
SEAM = math.floor(X0 / TILE) * TILE + TILE / 2  # where one mosaic ends and the next begins: across the middle of a tile
PIXEL, SPAN = 4, 4000  # the stand-in mosaics: 4 m pixels, 4 km tall


def height(x, y):
    return 100 + 0.02 * (x - X0) + 0.01 * (y - Y0)


def write_mosaic(path, west, east):
    w, h = round((east - west) / PIXEL), SPAN // PIXEL
    north = math.floor(Y0 / TILE) * TILE + SPAN / 2
    xs = west + PIXEL * (np.arange(w) + 0.5)
    ys = north - PIXEL * (np.arange(h) + 0.5)
    data = height(xs[None, :], ys[:, None]).astype("float32")
    profile = dict(driver="GTiff", height=h, width=w, count=1, dtype="float32", crs=LAMBERT, nodata=NODATA)
    with rasterio.open(path, "w", transform=from_origin(west, north, PIXEL, PIXEL), **profile) as dst:
        dst.write(data, 1)
    return path


def square_loop(side=600):
    """A square loop round the point, as (lat, lon)."""
    utm = utm_for(LON, LAT)
    to_utm = Transformer.from_crs("EPSG:4326", utm, always_xy=True)
    to_ll = Transformer.from_crs(utm, "EPSG:4326", always_xy=True)
    cx, cy = to_utm.transform(LON, LAT)
    corners = [(cx - side / 2, cy - side / 2), (cx + side / 2, cy - side / 2), (cx + side / 2, cy + side / 2)]
    corners += [(cx - side / 2, cy + side / 2), (cx - side / 2, cy - side / 2)]
    pts = []
    for (ax, ay), (bx, by) in zip(corners, corners[1:]):
        pts += [(ax + (bx - ax) * k / 20, ay + (by - ay) * k / 20) for k in range(20)]
    return [(lat, lon) for lon, lat in (to_ll.transform(x, y) for x, y in pts)]


@pytest.fixture
def mosaics(tmp_path):
    left = SEAM - SPAN / 2
    return [
        str(write_mosaic(tmp_path / "west.tif", left, SEAM)),
        str(write_mosaic(tmp_path / "east.tif", SEAM, SEAM + SPAN / 2)),
    ]


def test_tiles_cover_the_turned_square_and_the_road():
    utm = utm_for(LON, LAT)
    to_utm = Transformer.from_crs("EPSG:4326", utm, always_xy=True)
    points, _ = make_loop([to_utm.transform(lon, lat) for lat, lon in square_loop()], close=True)
    tiles = tiles_for(points, utm, 195)
    coarse = {(x, y) for x, y, r in tiles if r == COARSE}
    fine = {(x, y) for x, y, r in tiles if r == FINE}
    # every corner of the builder's square, in Lambert, falls in a coarse tile
    frame = square_around(points, utm, 195)
    to_lcc = Transformer.from_crs(utm, LAMBERT, always_xy=True)
    for dx in (-1, 1):
        for dy in (-1, 1):
            x, y = to_lcc.transform(frame.cx + dx * frame.half, frame.cy + dy * frame.half)
            assert (math.floor(x / TILE) * TILE, math.floor(y / TILE) * TILE) in coarse
    # and every road point in a fine one
    for p in points:
        x, y = to_lcc.transform(*p)
        assert (math.floor(x / TILE) * TILE, math.floor(y / TILE) * TILE) in fine
    # the box is round a turned square, so it is bigger than the square
    x0, y0, x1, y1 = square_in_lambert(frame)
    assert x1 - x0 > frame.size * 1.1


def test_tiles_join_the_mosaics_at_the_seam(tmp_path, mosaics):
    paths = fetch(square_loop(), tmp_path / "tiles", 195, log=lambda *_: None, sources=mosaics)
    assert paths and all(p.exists() for p in paths)
    seam_tiles = 0
    for p in paths:
        with rasterio.open(p) as src:
            res = src.res[0]
            a = src.read(1)
            assert res in (FINE, COARSE) and src.crs == LAMBERT
            xs = src.bounds.left + res * (np.arange(src.width) + 0.5)
            ys = src.bounds.top - res * (np.arange(src.height) + 0.5)
            want = height(xs[None, :], ys[:, None])
            inside = (np.abs(ys - Y0) < SPAN / 2 - 2 * res)[:, None] & np.ones_like(want, dtype=bool)
            assert np.all(a[inside] != NODATA), f"{p.name} has holes inside the mosaics"
            assert np.allclose(a[inside], want[inside], atol=0.1), p.name
            if src.bounds.left < SEAM < src.bounds.right:
                seam_tiles += 1
    assert seam_tiles >= 2, "some tiles should take from both mosaics"


def test_a_second_run_fetches_nothing(tmp_path, mosaics):
    logged = []
    fetch(square_loop(), tmp_path / "tiles", 195, log=lambda *_: None, sources=mosaics)
    fetch(square_loop(), tmp_path / "tiles", 195, log=logged.append, sources=mosaics)
    assert logged[0].endswith(", 0 to fetch")


def test_outside_every_mosaic_is_no_data(tmp_path, mosaics):
    paths = fetch(square_loop(), tmp_path / "tiles", 195, log=lambda *_: None, sources=mosaics[:1])  # west only
    east_pixels = 0
    for p in paths:
        with rasterio.open(p) as src:
            xs = src.bounds.left + src.res[0] * (np.arange(src.width) + 0.5)
            east = src.read(1)[:, xs > SEAM]
            assert np.all(east == NODATA), p.name
            east_pixels += east.size
    assert east_pixels > 0
