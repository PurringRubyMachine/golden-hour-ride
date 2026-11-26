"""fetch-hrdem: Natural Resources Canada's HRDEM terrain model for a route in Canada.

HRDEM comes as province-sized cloud-optimised GeoTIFF mosaics (a 1 m DTM, in Canada Atlas Lambert, EPSG:3979), listed
in a STAC catalogue. Cloud-optimised files can be read in pieces over HTTP, so this reads only what a route needs and
writes it as small GeoTIFFs: 2 m tiles along the road, for road heights, and 10 m tiles over the whole terrain square,
1 km each. Tiles already in the folder are not fetched again.
The data is © Natural Resources Canada, under the Open Government Licence – Canada.
"""

import json
import math
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

import numpy as np
import rasterio
from pyproj import CRS, Transformer
from rasterio.enums import Resampling
from rasterio.transform import from_origin
from rasterio.windows import from_bounds

from . import BuildError
from .frame import square_around, utm_for
from .route import make_loop

STAC = "https://datacube.services.geo.ca/stac/api/search"
COLLECTION = "hrdem-mosaic-1m"
DATASET = "https://open.canada.ca/data/en/dataset/0fe65119-e96e-4a57-8bfe-9d9245fba06b"
USER_AGENT = "golden-hour-ride-coursebuilder"
TILE = 1000  # metres
FINE, COARSE = 2, 10  # metres per pixel
NEAR_ROAD = 25  # fine tiles cover this far either side of the road
NODATA = -32767.0

# What to pass to `build` for data fetched with this command.
CREDIT_ARGS = [
    "--heights-credit",
    "Heights: Natural Resources Canada HRDEM, Open Government Licence – Canada.",
    "--heights-licence",
    "OGL-Canada-2.0",
    "--heights-url",
    DATASET,
]

LAMBERT = CRS.from_epsg(3979)  # Canada Atlas Lambert, the mosaics' own system


def square_in_lambert(frame):
    """The box in EPSG:3979 that holds the terrain square. The builder works in UTM, whose grid is turned some
    degrees against Lambert's, so the box is round the turned square, sampled along its edges."""
    to_lcc = Transformer.from_crs(frame.crs, LAMBERT, always_xy=True)
    h = frame.half + frame.cell
    edge = [-h + 2 * h * k / 8 for k in range(9)]
    pts = [(frame.cx + a, frame.cy + b) for a in edge for b in (-h, h)] + [
        (frame.cx + a, frame.cy + b) for a in (-h, h) for b in edge
    ]
    xs, ys = zip(*(to_lcc.transform(x, y) for x, y in pts))
    return min(xs), min(ys), max(xs), max(ys)


def tiles_for(points_utm, utm, margin):
    """The (east, north, resolution) of each tile needed, in EPSG:3979: fine near the road, coarse over the square."""
    x0, y0, x1, y1 = square_in_lambert(square_around(points_utm, utm, margin))
    span = lambda a, b: range(math.floor(a / TILE), math.floor(b / TILE) + 1)  # noqa: E731
    coarse = {(i * TILE, j * TILE, COARSE) for i in span(x0, x1) for j in span(y0, y1)}
    to_lcc = Transformer.from_crs(utm, LAMBERT, always_xy=True)
    fine = {
        (math.floor((x + dx) / TILE) * TILE, math.floor((y + dy) / TILE) * TILE, FINE)
        for x, y in (to_lcc.transform(*p) for p in points_utm)
        for dx in (-NEAR_ROAD, NEAR_ROAD)
        for dy in (-NEAR_ROAD, NEAR_ROAD)
    }
    return sorted(coarse) + sorted(fine)


def search(bbox_lonlat, stac=STAC):
    """The DTM mosaics that cover an area: their URLs, from the STAC catalogue."""
    q = urllib.parse.urlencode({"collections": COLLECTION, "bbox": ",".join(f"{v:.6f}" for v in bbox_lonlat)})
    request = urllib.request.Request(f"{stac}?{q}&limit=50", headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(request, timeout=60) as r:
            found = json.load(r)
    except (urllib.error.URLError, TimeoutError, ConnectionError) as ex:
        raise BuildError(f"could not reach the HRDEM catalogue: {getattr(ex, 'reason', ex)}") from ex
    urls = [f["assets"]["dtm"]["href"] for f in found.get("features", []) if "dtm" in f.get("assets", {})]
    if not urls:
        raise BuildError("HRDEM has no terrain model for this area: is the route in Canada, and covered by LiDAR?")
    return urls


def read_tile(sources, x, y, res):
    """One tile from whichever mosaics overlap it: their valid pixels, averaged down to `res` metres."""
    n = TILE // res
    out = np.full((n, n), NODATA, dtype="float32")
    for src in sources:
        b = src.bounds
        ix0, iy0, ix1, iy1 = max(x, b.left), max(y, b.bottom), min(x + TILE, b.right), min(y + TILE, b.top)
        if ix1 - ix0 < res or iy1 - iy0 < res:
            continue
        # snap the overlap to this tile's pixels
        c0, c1 = round((ix0 - x) / res), round((ix1 - x) / res)
        r0, r1 = round((y + TILE - iy1) / res), round((y + TILE - iy0) / res)
        window = from_bounds(x + c0 * res, y + TILE - r1 * res, x + c1 * res, y + TILE - r0 * res, src.transform)
        a = src.read(1, window=window, out_shape=(r1 - r0, c1 - c0), resampling=Resampling.average)
        valid = np.isfinite(a) & (a != src.nodata) & (a > -1000)
        part = out[r0:r1, c0:c1]
        take = (part == NODATA) & valid
        part[take] = a[take]
    return out


def write_tile(path, data, x, y, res):
    tmp = path.with_suffix(".part")
    profile = dict(driver="GTiff", height=data.shape[0], width=data.shape[1], count=1, dtype="float32")
    profile.update(crs=LAMBERT, transform=from_origin(x, y + TILE, res, res), nodata=NODATA, compress="deflate")
    with rasterio.open(tmp, "w", **profile) as dst:
        dst.write(data, 1)
    tmp.replace(path)


def fetch(points_latlon, out_dir, margin, log=print, sources=None):
    """Read the tiles a route needs into out_dir. Returns the tile paths.

    sources: the mosaics to read, as paths or URLs; by default, those the STAC catalogue lists for the area.
    """
    lat = sum(p[0] for p in points_latlon) / len(points_latlon)
    lon = sum(p[1] for p in points_latlon) / len(points_latlon)
    utm = utm_for(lon, lat)
    to_utm = Transformer.from_crs("EPSG:4326", utm, always_xy=True)
    # every 5 m along the route, so no stretch of road between sparse GPX points misses its fine tiles
    points, _ = make_loop([to_utm.transform(lo, la) for la, lo in points_latlon], close=True)
    tiles = tiles_for(points, utm, margin)
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    paths = {(x, y, res): out / f"hrdem_{res}m_{x}_{y}.tif" for x, y, res in tiles}
    todo = [(tile, path) for tile, path in paths.items() if not path.exists()]
    log(f"{len(paths)} tiles needed, {len(todo)} to fetch")
    if not todo:
        return list(paths.values())

    if sources is None:
        to_ll = Transformer.from_crs(LAMBERT, "EPSG:4326", always_xy=True)
        xs = [t[0] for t in tiles] + [t[0] + TILE for t in tiles]
        ys = [t[1] for t in tiles] + [t[1] + TILE for t in tiles]
        corners = [to_ll.transform(x, y) for x in (min(xs), max(xs)) for y in (min(ys), max(ys))]
        sources = search(
            (
                min(c[0] for c in corners),
                min(c[1] for c in corners),
                max(c[0] for c in corners),
                max(c[1] for c in corners),
            )
        )
        log(f"HRDEM mosaics here: {', '.join(Path(u).name for u in sources)}")
    remote = lambda s: f"/vsicurl/{s}" if str(s).startswith(("http://", "https://")) else str(s)  # noqa: E731
    env = dict(
        GDAL_HTTP_USERAGENT=USER_AGENT,
        GDAL_DISABLE_READDIR_ON_OPEN="EMPTY_DIR",  # don't list the bucket looking for side files
        GDAL_HTTP_MAX_RETRY="5",
        GDAL_HTTP_RETRY_DELAY="3",
        CPL_VSIL_CURL_ALLOWED_EXTENSIONS=".tif",
    )
    with rasterio.Env(**env):
        opened = []
        try:
            for s in sources:
                src = rasterio.open(remote(s))
                if src.crs is None or CRS.from_user_input(src.crs) != LAMBERT:
                    raise BuildError(f"{s} is not in Canada Atlas Lambert (EPSG:3979), as HRDEM mosaics are")
                opened.append(src)
            for done, ((x, y, res), path) in enumerate(todo, 1):
                try:
                    write_tile(path, read_tile(opened, x, y, res), x, y, res)
                except rasterio.errors.RasterioIOError as ex:
                    raise BuildError(f"could not read HRDEM for tile {path.name}: {ex}") from ex
                log(f"  {done} of {len(todo)}: {path.name}")
        finally:
            for src in opened:
                src.close()
    return list(paths.values())
