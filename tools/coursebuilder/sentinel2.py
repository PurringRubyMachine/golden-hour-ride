"""fetch-sentinel2: a summer satellite photo of the ground for a route anywhere, from Copernicus Sentinel-2.

Sentinel-2 photographs all land every few days at 10 m per pixel. Earth Search (Element 84) lists its scenes in a STAC
catalogue, each with a cloud-optimised true-colour GeoTIFF (the "visual" asset), so this reads only the course's
square from the clearest summer scenes, filling any part one scene misses from the next, and writes it as one GeoTIFF
for `build --imagery`. Contains modified Copernicus Sentinel data, free to use with credit.
"""

import calendar
import json
import math
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

import numpy as np
import rasterio
from pyproj import Transformer
from rasterio.enums import Resampling
from rasterio.transform import from_origin
from rasterio.vrt import WarpedVRT

from . import BuildError
from .frame import square_around, utm_for
from .route import make_loop

STAC = "https://earth-search.aws.element84.com/v1/search"
COLLECTION = "sentinel-2-l2a"
USER_AGENT = "golden-hour-ride-coursebuilder"
RES = 10  # metres per pixel, Sentinel-2's own
MAX_SCENES = 6  # scenes tried to fill the square before giving up on the last gaps
LEGAL = "https://sentinels.copernicus.eu/documents/247904/690755/Sentinel_Data_Legal_Notice"


def credit_args(years):
    """What to pass to `build` for a photo made from scenes taken in these years."""
    span = f"{min(years)}" if min(years) == max(years) else f"{min(years)}–{max(years)}"
    return [
        "--imagery-credit",
        f"Ground from above: contains modified Copernicus Sentinel data {span}.",
        "--imagery-licence",
        "Copernicus Sentinel data licence",
        "--imagery-url",
        LEGAL,
    ]


def search(bbox_lonlat, years, months, max_cloud, stac=STAC):
    """Scenes over an area in the given months of the given years, clearest first, as STAC features."""
    found = []
    for year in years:
        when = f"{year}-{months[0]:02d}-01T00:00:00Z/{year}-{months[1]:02d}-{_last_day(year, months[1])}T23:59:59Z"
        q = urllib.parse.urlencode(
            {"collections": COLLECTION, "bbox": ",".join(f"{v:.6f}" for v in bbox_lonlat), "datetime": when}
        )
        request = urllib.request.Request(f"{stac}?{q}&limit=200", headers={"User-Agent": USER_AGENT})
        try:
            with urllib.request.urlopen(request, timeout=60) as r:
                found += json.load(r).get("features", [])
        except (urllib.error.URLError, TimeoutError, ConnectionError) as ex:
            raise BuildError(f"could not reach the Sentinel-2 catalogue: {getattr(ex, 'reason', ex)}") from ex
    return choose(found, max_cloud)


def choose(features, max_cloud):
    """The scenes worth reading, clearest first, and among equally clear ones the most complete."""
    usable = [
        f
        for f in features
        if "visual" in f.get("assets", {}) and f.get("properties", {}).get("eo:cloud_cover", 100) <= max_cloud
    ]
    usable.sort(
        key=lambda f: (
            round(f["properties"]["eo:cloud_cover"], 1),
            f["properties"].get("s2:nodata_pixel_percentage", 0),
        )
    )
    return usable


def _last_day(year, month):
    return calendar.monthrange(year, month)[1]


def fill_from(sources, crs, west, north, width, height):
    """Read the square (in `crs`, RES-metre pixels from its north-west corner) from each source in turn, keeping the
    first valid colour at every pixel. Returns (rgb as uint8 [3, h, w], how many pixels are still empty, sources
    used)."""
    out = np.zeros((3, height, width), dtype="uint8")
    empty = np.ones((height, width), dtype=bool)
    used = []
    transform = from_origin(west, north, RES, RES)
    for s in sources:
        with rasterio.open(s) as src:
            with WarpedVRT(
                src, crs=crs, transform=transform, width=width, height=height, resampling=Resampling.bilinear
            ) as vrt:
                rgb = vrt.read([1, 2, 3])
        valid = rgb.max(axis=0) > 0  # the true-colour files mark no data as black
        take = empty & valid
        if take.any():
            out[:, take] = rgb[:, take]
            empty &= ~take
            used.append(s)
        if not empty.any():
            break
    return out, int(empty.sum()), used


def fetch(points_latlon, out_dir, margin, years, months=(6, 8), max_cloud=5, log=print, sources=None):
    """Write sentinel2.tif, the course's square from the clearest summer scenes, into out_dir. Returns its path and
    the years of the scenes used.

    sources: (url or path, year) pairs to read instead of searching the catalogue.
    """
    lat = sum(p[0] for p in points_latlon) / len(points_latlon)
    lon = sum(p[1] for p in points_latlon) / len(points_latlon)
    utm = utm_for(lon, lat)
    to_utm = Transformer.from_crs("EPSG:4326", utm, always_xy=True)
    points, _ = make_loop([to_utm.transform(lo, la) for la, lo in points_latlon], close=True)
    frame = square_around(points, utm, margin)
    # a little more than the square, so the builder can turn it to its own coordinate system without bare corners
    h = math.ceil((frame.half + 200) / RES) * RES
    west, north, n = frame.cx - h, frame.cy + h, 2 * h // RES

    if sources is None:
        found = search(frame.bounds_lonlat(), years, months, max_cloud)
        if not found:
            raise BuildError(
                f"no Sentinel-2 scenes here with under {max_cloud} % cloud in those months: try more years "
                "(--years) or allow more cloud (--max-cloud)"
            )
        sources = [(f["assets"]["visual"]["href"], int(f["properties"]["datetime"][:4])) for f in found[:MAX_SCENES]]
        log("clearest scenes: " + ", ".join(f["id"] for f in found[:MAX_SCENES]))
    year_of = {s: y for s, y in sources}
    remote = lambda s: f"/vsicurl/{s}" if str(s).startswith(("http://", "https://")) else str(s)  # noqa: E731
    env = dict(
        GDAL_HTTP_USERAGENT=USER_AGENT,
        GDAL_DISABLE_READDIR_ON_OPEN="EMPTY_DIR",
        GDAL_HTTP_MAX_RETRY="5",
        GDAL_HTTP_RETRY_DELAY="3",
        CPL_VSIL_CURL_ALLOWED_EXTENSIONS=".tif",
    )
    with rasterio.Env(**env):
        try:
            rgb, empty, used = fill_from([remote(s) for s, _ in sources], utm, west, north, n, n)
        except rasterio.errors.RasterioIOError as ex:
            raise BuildError(f"could not read a Sentinel-2 scene: {ex}") from ex
    if not used:
        raise BuildError("none of the scenes cover the course's square")
    if empty:
        log(f"warning: {empty} pixels ({100 * empty / n / n:.1f} %) are not covered by any scene and are left black")
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    path = out / "sentinel2.tif"
    profile = dict(driver="GTiff", width=n, height=n, count=3, dtype="uint8", crs=utm, nodata=0, compress="deflate")
    with rasterio.open(path, "w", transform=from_origin(west, north, RES, RES), photometric="RGB", **profile) as dst:
        dst.write(rgb)
        dst.update_tags(scenes=" ".join(Path(str(s)).parent.name or str(s) for s in used))
    by_name = {remote(s): s for s, _ in sources}
    years_used = sorted({year_of[by_name[s]] for s in used})
    log(f"wrote {path}: {n} × {n} pixels, from {len(used)} scene{'s' if len(used) > 1 else ''}")
    return path, years_used
