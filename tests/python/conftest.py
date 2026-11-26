"""Helpers for the course builder tests: synthetic DTMs and routes."""

import numpy as np
import pytest
import rasterio
from pyproj import Transformer
from rasterio.transform import from_origin

UTM = "EPSG:32630"  # WGS 84 / UTM zone 30N: south-west England, true to scale near 3° W
E0, N0 = 500_000.0, 5_700_000.0  # a point in it (about 51.45° N, 3.0° W)


def plane(e, n):
    """The test ground: rises 3 % to the east and 1 % to the north."""
    return 100.0 + 0.03 * (e - E0) + 0.01 * (n - N0)


def write_dtm(path, crs, west, north, res, width, height, height_at=plane, nodata=-9999.0, hole=None):
    """A GeoTIFF whose pixels hold height_at(easting, northing) in UTM, evaluated at each pixel centre.

    hole: (west, south, east, north) in UTM, left as no data.
    """
    cols, rows = np.meshgrid(np.arange(width) + 0.5, np.arange(height) + 0.5)
    x, y = west + cols * res, north - rows * res
    if crs != UTM:
        x, y = Transformer.from_crs(crs, UTM, always_xy=True).transform(x, y)
    data = height_at(x, y).astype("float32")
    if hole:
        w, s, e, n = hole
        data[(x > w) & (x < e) & (y > s) & (y < n)] = nodata
    with rasterio.open(
        path, "w", driver="GTiff", width=width, height=height, count=1, dtype="float32",
        crs=crs, transform=from_origin(west, north, res, res), nodata=nodata,
    ) as dst:  # fmt: skip
        dst.write(data, 1)
    return path


def square_route(side=600.0, step=20.0, e=E0, n=N0):
    """A square loop in UTM, anticlockwise from the south-west corner, as points every `step` metres."""
    corners = [(e - side / 2, n - side / 2), (e + side / 2, n - side / 2), (e + side / 2, n + side / 2),
               (e - side / 2, n + side / 2)]  # fmt: skip
    pts = []
    for (ax, ay), (bx, by) in zip(corners, corners[1:] + corners[:1]):
        k = int(side / step)
        pts += [(ax + (bx - ax) * i / k, ay + (by - ay) * i / k) for i in range(k)]
    return pts + [pts[0]]


def write_gpx(path, utm_points, kind="trk"):
    """A GPX file of UTM points: a track (kind='trk') or a route ('rte')."""
    to_ll = Transformer.from_crs(UTM, "EPSG:4326", always_xy=True)
    tag = "trkpt" if kind == "trk" else "rtept"
    pts = "".join(
        f'<{tag} lat="{lat:.8f}" lon="{lon:.8f}"/>' for lon, lat in (to_ll.transform(x, y) for x, y in utm_points)
    )
    body = f"<trk><trkseg>{pts}</trkseg></trk>" if kind == "trk" else f"<rte>{pts}</rte>"
    path.write_text(f'<?xml version="1.0"?><gpx version="1.1" xmlns="http://www.topografix.com/GPX/1/1">{body}</gpx>')
    return path


@pytest.fixture
def options(tmp_path):
    """Build options for a 600 m square loop on the plane, with a small margin and no network."""
    from tools.coursebuilder.build import Options

    def make(**kw):
        defaults = dict(
            id="test-loop",
            name="Test loop",
            route=str(write_gpx(tmp_path / "route.gpx", square_route())),
            dtm=[str(tmp_path / "dtm")],
            heights_credit="Heights: a test plane",
            heights_licence="CC0-1.0",
            margin=195,  # 600 m + 2 × 195 m rounds up to a 1000 m square
            osm=False,
            courses_dir=str(tmp_path / "courses"),
            cache_dir=str(tmp_path / "cache"),
        )
        defaults.update(kw)
        return Options(**defaults)

    (tmp_path / "dtm").mkdir()
    return make
