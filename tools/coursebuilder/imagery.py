"""The ground from above: aerial or satellite photos turned onto the course's terrain square, as ground.jpg.

The photo covers the square exactly, north edge at the top, like terrain.bin. It is at most MAX_PIXELS across, at
about 3–4 m per pixel, and its brightness is evened out, so photos from different sources and days sit in the scene
alike.
The app shows it in the distance, where the ground's own colour rules can't show fields, lakes and towns.
"""

import warnings
from pathlib import Path

import numpy as np
import rasterio
from rasterio.enums import Resampling
from rasterio.transform import from_origin
from rasterio.vrt import WarpedVRT

from . import BuildError

FILE = "ground.jpg"
MAX_PIXELS = 4096  # every graphics chip the ride supports loads a texture this size
TARGET = 4  # metres per pixel, or finer: the size is the next power of two up
BUDGET = 2_500_000  # bytes: the JPEG's quality is lowered until it fits
QUALITIES = (88, 82, 76, 70, 64, 58, 52)
LOW, HIGH = 1, 99  # percentiles stretched to the ends of the range
FLOOR, CEILING = 12, 235  # where they go: no pure black or white, which no ground is


def pixels_for(size):
    """How many pixels across for a square `size` metres wide: a power of two, at most MAX_PIXELS, fine enough for
    TARGET metres per pixel where it can be."""
    n = 256
    while n < MAX_PIXELS and size / n > TARGET:
        n *= 2
    return n


def read_square(paths, frame, n):
    """The photos over the square, n × n pixels, as uint8 [3, n, n], and a mask of the pixels no photo covers. Earlier
    files win where they overlap."""
    out = np.zeros((3, n, n), dtype="uint8")
    empty = np.ones((n, n), dtype=bool)
    res = frame.size / n
    transform = from_origin(frame.cx - frame.half, frame.cy + frame.half, res, res)
    for path in paths:
        try:
            src = rasterio.open(path)
        except rasterio.errors.RasterioIOError as ex:
            raise BuildError(f"can't read {Path(path).name} as an image: {ex}") from ex
        with src:
            if src.crs is None:
                raise BuildError(f"{Path(path).name} has no coordinate system, so it can't be placed on the map")
            if src.count < 3:
                raise BuildError(
                    f"{Path(path).name} has {src.count} band(s): a colour photo (red, green, blue) is needed"
                )
            if src.dtypes[0] != "uint8":
                raise BuildError(f"{Path(path).name} is {src.dtypes[0]}: an 8-bit colour photo is needed")
            with WarpedVRT(
                src, crs=frame.crs, transform=transform, width=n, height=n, resampling=Resampling.average
            ) as vrt:
                rgb = vrt.read([1, 2, 3])
                alpha = vrt.dataset_mask()
        valid = (alpha > 0) & (rgb.max(axis=0) > 0)
        take = empty & valid
        out[:, take] = rgb[:, take]
        empty &= ~take
    return out, empty


def even_colours(rgb, empty):
    """Stretch the brightness from its LOW to its HIGH percentile (over the covered pixels, all colours together) to
    FLOOR..CEILING, the same for red, green and blue, so a dull or dark photo is brought to the same range as any other
    but keeps its colours: stretching each colour on its own turns forest bright green and lakes purple. Uncovered
    pixels get the average colour."""
    covered = ~empty
    values = rgb[:, covered].astype("float32")
    lo, hi = np.percentile(values, (LOW, HIGH))
    out = FLOOR + (rgb.astype("float32") - lo) / max(hi - lo, 1.0) * (CEILING - FLOOR)
    out[:, empty] = out[:, covered].mean(axis=1)[:, None]
    return np.clip(np.round(out), 0, 255).astype("uint8")


def write_jpeg(path, rgb, budget=BUDGET):
    """Write rgb as a JPEG, at the best quality that fits the budget. Returns the quality used."""
    path = Path(path)
    for q in QUALITIES:
        # no .aux.xml beside it, and no map position in it: the course places it
        with rasterio.Env(GDAL_PAM_ENABLED="NO"), warnings.catch_warnings():
            warnings.simplefilter("ignore", rasterio.errors.NotGeoreferencedWarning)
            with rasterio.open(
                path, "w", driver="JPEG", width=rgb.shape[2], height=rgb.shape[1], count=3, dtype="uint8", quality=q
            ) as dst:
                dst.write(rgb)
        if path.stat().st_size <= budget:
            return q
    return q


def bake(paths, frame, folder, log=print):
    """Write folder/ground.jpg from the photos. Returns course.json's imagery field."""
    n = pixels_for(frame.size)
    rgb, empty = read_square(paths, frame, n)
    share = empty.mean()
    if share == 1:
        raise BuildError("the imagery files don't cover the terrain square at all: are they the right area?")
    if share > 0:
        log(f"imagery: {100 * share:.1f} % of the square isn't covered by the photos and is filled with their average")
    folder = Path(folder)
    folder.mkdir(parents=True, exist_ok=True)
    q = write_jpeg(folder / FILE, even_colours(rgb, empty))
    size = (folder / FILE).stat().st_size
    log(f"imagery: {FILE}, {n} × {n} pixels ({frame.size / n:.1f} m each), {size / 1e6:.1f} MB at quality {q}")
    return {"file": FILE, "size": n}
