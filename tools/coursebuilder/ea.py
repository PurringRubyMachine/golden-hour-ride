"""fetch-ea: Environment Agency LiDAR Composite DTM tiles for a route in England.

Downloads GeoTIFFs from the Environment Agency's coverage service (WCS): 2 m tiles along the road, for road heights,
and 10 m tiles over the whole terrain square. Tiles already in the folder are not fetched again.
The data is © Environment Agency, under the Open Government Licence v3.0.
"""

import http.client
import math
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from pyproj import CRS, Transformer

from . import BuildError
from .frame import square_around
from .route import make_loop

WCS = "https://environment.data.gov.uk/geoservices/datasets/13787b9a-26a4-4775-8523-806d13af58fc/wcs"
COVERAGE = "13787b9a-26a4-4775-8523-806d13af58fc__Lidar_Composite_Elevation_DTM_1m"
USER_AGENT = "golden-hour-ride-coursebuilder"
TILE = 1000  # metres
FINE, COARSE = 2, 10  # metres per pixel
NEAR_ROAD = 25  # fine tiles cover this far either side of the road

# What to pass to `build` for data fetched with this command.
CREDIT_ARGS = [
    "--heights-credit",
    "Heights: Environment Agency LiDAR, Open Government Licence.",
    "--heights-licence",
    "OGL-UK-3.0",
    "--heights-url",
    "https://environment.data.gov.uk/survey",
]

BNG = CRS.from_epsg(27700)  # British National Grid, the coverage's own system


def tile_url(e, n, res):
    return (
        f"{WCS}?service=WCS&version=2.0.1&request=GetCoverage&coverageId={COVERAGE}"
        f"&subset=E({e},{e + TILE})&subset=N({n},{n + TILE})&format=image/tiff&scalefactor={1 / res:g}"
    )


def tiles_for(points_bng, margin):
    """The (east, north, resolution) of each tile needed: fine near the road, coarse over the terrain square."""
    frame = square_around(points_bng, BNG, margin)
    h = frame.half + frame.cell
    span = lambda a, b: range(math.floor(a / TILE), math.floor(b / TILE) + 1)  # noqa: E731
    coarse = {
        (i * TILE, j * TILE, COARSE) for i in span(frame.cx - h, frame.cx + h) for j in span(frame.cy - h, frame.cy + h)
    }
    fine = {
        (math.floor((x + dx) / TILE) * TILE, math.floor((y + dy) / TILE) * TILE, FINE)
        for x, y in points_bng
        for dx in (-NEAR_ROAD, NEAR_ROAD)
        for dy in (-NEAR_ROAD, NEAR_ROAD)
    }
    return sorted(coarse) + sorted(fine)


def download(url, path, tries=8):
    """Fetch a URL to a file, trying again when the service is busy, slow or drops the connection."""
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    for attempt in range(tries):
        try:
            with urllib.request.urlopen(request, timeout=60) as r:
                data = r.read()
            break
        except urllib.error.HTTPError as ex:
            if ex.code not in (429, 500, 502, 503, 504) or attempt == tries - 1:
                raise BuildError(f"the Environment Agency service refused {url}: {ex}") from ex
        except (TimeoutError, ConnectionError, http.client.HTTPException, urllib.error.URLError) as ex:
            if attempt == tries - 1:
                reason = getattr(ex, "reason", ex)
                raise BuildError(f"could not reach the Environment Agency service: {reason}") from ex
        time.sleep(4 + attempt * 4)
    if not data.startswith((b"II*\0", b"MM\0*")):
        raise BuildError(f"the Environment Agency service sent something other than a GeoTIFF for {url}")
    tmp = path.with_suffix(".part")
    tmp.write_bytes(data)
    tmp.replace(path)


def fetch(points_latlon, out_dir, margin, log=print):
    """Download the tiles a route needs into out_dir, two at a time. Returns the tile paths."""
    to_bng = Transformer.from_crs("EPSG:4326", BNG, always_xy=True)
    # every 5 m along the route, so no stretch of road between sparse GPX points misses its fine tiles
    points, _ = make_loop([to_bng.transform(lon, lat) for lat, lon in points_latlon], close=True)
    xs, ys = [p[0] for p in points], [p[1] for p in points]
    if min(xs) < 0 or max(xs) > 700_000 or min(ys) < 0 or max(ys) > 1_300_000:
        raise BuildError("this route is outside Great Britain; the Environment Agency covers England only")
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    paths = {(e, n, res): out / f"ea_{res}m_{e}_{n}.tif" for e, n, res in tiles_for(points, margin)}
    todo = [(tile, path) for tile, path in paths.items() if not path.exists()]
    log(f"{len(paths)} tiles needed, {len(todo)} to fetch")
    done = 0

    def get(item):
        (e, n, res), path = item
        download(tile_url(e, n, res), path)
        return path

    with ThreadPoolExecutor(2) as pool:  # two at a time: the service limits how fast one client may ask
        for path in pool.map(get, todo):
            done += 1
            log(f"  {done} of {len(todo)}: {path.name}")
    return list(paths.values())
