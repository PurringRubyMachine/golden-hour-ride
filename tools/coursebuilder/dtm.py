"""Heights from DTM files: any raster GDAL can read, in any coordinate system, mixed resolutions allowed.

Each file is reprojected on the fly into the working coordinate system. Where files overlap, the finest wins.
"""

import math
from pathlib import Path

import numpy as np
import rasterio
from rasterio.enums import Resampling
from rasterio.fill import fillnodata
from rasterio.transform import from_origin
from rasterio.warp import reproject, transform_bounds

from . import BuildError

RASTER_SUFFIXES = {".tif", ".tiff", ".asc", ".img", ".vrt", ".dem", ".bil", ".flt"}
SANE = (-500.0, 9000.0)  # heights outside this range are treated as no data
FINE_TILE, FINE_RES = 250, 2  # road heights: 250 m tiles at 2 m
FILL_CELLS = 20  # terrain holes are filled from data up to this many cells away


def expand(paths):
    """DTM paths, with any folder replaced by the rasters inside it."""
    out = []
    for p in map(Path, paths):
        if p.is_dir():
            out += sorted(f for f in p.iterdir() if f.suffix.lower() in RASTER_SUFFIXES)
        elif p.exists():
            out.append(p)
        else:
            raise BuildError(f"DTM file not found: {p}")
    if not out:
        raise BuildError("no DTM files found")
    return out


def pixel_metres(src):
    """A raster's pixel size in metres, roughly (degrees are converted at the raster's centre)."""
    size = abs(src.transform.a)
    if src.crs and src.crs.is_geographic:
        lat = (src.bounds.bottom + src.bounds.top) / 2
        size *= 111_320 * math.cos(math.radians(lat))
    return size


class Dtm:
    """A set of DTM files, read in the working coordinate system."""

    def __init__(self, paths, crs=None):
        self.sources = []
        for p in expand(paths):
            try:
                src = rasterio.open(p)
            except rasterio.RasterioIOError as ex:
                raise BuildError(f"could not read DTM {p}: {ex}") from ex
            if src.crs is None:
                raise BuildError(f"{p} does not say what coordinate system it is in")
            self.sources.append(src)
        self._first = self.sources[0].crs
        self.sources.sort(key=pixel_metres, reverse=True)  # coarsest first, so finer files overwrite it
        self.crs = crs
        self._tiles = {}
        self._bounds = {}  # each file's bounds in the working system, worked out once: see bounds()

    def first_crs(self):
        """The coordinate system of the first file given."""
        return self._first

    def close(self):
        for src in self.sources:
            src.close()

    def bounds(self, src):
        """A file's bounds in the working coordinate system. Cached: a long route asks for every file's bounds for
        each of hundreds of fine tiles, and converting them each time took most of the build."""
        key = (src.name, self.crs)
        if key not in self._bounds:
            self._bounds[key] = transform_bounds(src.crs, self.crs, *src.bounds)
        return self._bounds[key]

    def grid(self, west, north, res, width, height, resampling):
        """Heights on a grid whose top-left pixel corner is (west, north), NaN where there is no data."""
        out = np.full((height, width), np.nan, dtype=np.float32)
        transform = from_origin(west, north, res, res)
        box = (west, north - height * res, west + width * res, north)
        for src in self.sources:
            b = self.bounds(src)
            if b[0] > box[2] or b[2] < box[0] or b[1] > box[3] or b[3] < box[1]:
                continue  # this file doesn't reach the grid
            layer = np.full_like(out, np.nan)
            reproject(
                source=rasterio.band(src, 1),
                destination=layer,
                src_nodata=src.nodata,
                dst_transform=transform,
                dst_crs=self.crs,
                dst_nodata=np.nan,
                resampling=resampling,
            )
            layer[(layer < SANE[0]) | (layer > SANE[1])] = np.nan
            ok = ~np.isnan(layer)
            out[ok] = layer[ok]
        return out

    # --- fine heights along the road

    def load_fine(self, points, reach=12):
        """Fetch the fine tiles covering `reach` metres around each point."""
        keys = {
            (math.floor((x + dx) / FINE_TILE), math.floor((y + dy) / FINE_TILE))
            for x, y in points
            for dx in (-reach, reach)
            for dy in (-reach, reach)
        }
        n = FINE_TILE // FINE_RES
        for i, j in sorted(keys - self._tiles.keys()):
            g = self.grid(i * FINE_TILE, (j + 1) * FINE_TILE, FINE_RES, n, n, Resampling.bilinear)
            self._tiles[(i, j)] = None if np.isnan(g).all() else g

    def fine(self, x, y):
        """The height at a point from the fine tiles (bilinear between pixel centres), or None without data."""
        i, j = math.floor(x / FINE_TILE), math.floor(y / FINE_TILE)
        g = self._tiles.get((i, j))
        if g is None:
            return None
        h, w = g.shape
        fx = (x - i * FINE_TILE) / FINE_RES - 0.5
        fy = ((j + 1) * FINE_TILE - y) / FINE_RES - 0.5
        x0, y0 = max(0, min(w - 2, math.floor(fx))), max(0, min(h - 2, math.floor(fy)))
        u, v = min(1.0, max(0.0, fx - x0)), min(1.0, max(0.0, fy - y0))
        q = g[y0 : y0 + 2, x0 : x0 + 2]
        if np.isnan(q).any():
            return None
        return float((q[0, 0] * (1 - u) + q[0, 1] * u) * (1 - v) + (q[1, 0] * (1 - u) + q[1, 1] * u) * v)

    # --- the terrain grid

    def terrain(self, frame):
        """Heights at every terrain grid point, row 0 at the north edge, each the mean over its cell.

        Returns (heights, filled), where filled counts the grid points that had no data and were filled in.
        """
        n, c = frame.cells + 1, frame.cell
        g = self.grid(frame.cx - frame.half - c / 2, frame.cy + frame.half + c / 2, c, n, n, Resampling.average)
        missing = np.isnan(g)
        share = missing.mean()
        if share == 1:
            raise BuildError("the DTM files don't cover the route at all: are they the right area?")
        if share > 0.01:
            raise BuildError(f"{share:.0%} of the terrain square has no DTM data: {_where(frame, missing)}")
        if missing.any():
            g = fillnodata(g, mask=(~missing).astype(np.uint8), max_search_distance=FILL_CELLS, smoothing_iterations=0)
            left = np.isnan(g)
            if left.any():
                raise BuildError(f"the DTM has a gap too wide to fill: {_where(frame, left)}")
        return g, int(missing.sum())


def _where(frame, missing):
    """Where the missing data is, in words a person can check on a map."""
    rows, cols = np.nonzero(missing)
    t = frame.lonlat()
    x0, x1 = frame.cx - frame.half + cols.min() * frame.cell, frame.cx - frame.half + cols.max() * frame.cell
    y0, y1 = frame.cy + frame.half - rows.max() * frame.cell, frame.cy + frame.half - rows.min() * frame.cell
    (w, s), (e, n) = t.transform(x0, y0), t.transform(x1, y1)
    edge = rows.min() == 0 or cols.min() == 0 or rows.max() == frame.cells or cols.max() == frame.cells
    hint = " It reaches the edge of the square, so a smaller --margin may help." if edge else ""
    return f"between latitude {s:.4f} and {n:.4f}, longitude {w:.4f} and {e:.4f}.{hint}"
