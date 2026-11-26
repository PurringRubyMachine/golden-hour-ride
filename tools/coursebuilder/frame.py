"""The working coordinate system and the course's local frame.

The ride works in local metres: x east, y up, z south, with the origin at the centre of the terrain square.
"""

import math
from dataclasses import dataclass

from pyproj import CRS, Proj, Transformer
from pyproj.aoi import AreaOfInterest
from pyproj.database import query_utm_crs_info

CELL = 10  # terrain grid spacing, metres
MAX_SCALE_ERROR = 0.001  # a projection that stretches distances more than 0.1 % is not used as it is


def horizontal(crs):
    """The horizontal part of a coordinate system that may also carry heights (a compound one)."""
    crs = CRS.from_user_input(crs)
    return crs.sub_crs_list[0] if crs.is_compound else crs


def scale_error(crs, lon, lat):
    """How much the projection stretches or shrinks distances at a point, as a fraction."""
    f = Proj(crs).get_factors(lon, lat)
    return max(abs(f.meridional_scale - 1), abs(f.parallel_scale - 1))


def utm_for(lon, lat):
    """The WGS 84 UTM zone for a point."""
    found = query_utm_crs_info(datum_name="WGS 84", area_of_interest=AreaOfInterest(lon, lat, lon, lat))
    return CRS.from_epsg(found[0].code)


def choose_crs(dtm_crs, lon, lat):
    """The DTM's own coordinate system if it is projected in metres and true to scale at the route, else UTM."""
    if dtm_crs is not None:
        crs = horizontal(dtm_crs)
        metres = all(a.unit_name in ("metre", "meter") for a in crs.axis_info)
        if crs.is_projected and metres and scale_error(crs, lon, lat) < MAX_SCALE_ERROR:
            return crs
    return utm_for(lon, lat)


def crs_name(crs):
    """A short name for a coordinate system: 'EPSG:27700' where there is a code, else its full description."""
    code = crs.to_epsg()
    return f"EPSG:{code}" if code else crs.to_string()


@dataclass
class Frame:
    """The terrain square, centred on (cx, cy) in the working coordinate system, `size` metres across."""

    crs: CRS
    cx: float
    cy: float
    size: int
    cell: int = CELL

    @property
    def cells(self):
        return self.size // self.cell

    @property
    def half(self):
        return self.size / 2

    def local(self, x, y):
        """Working coordinates to local (x east, z south)."""
        return x - self.cx, -(y - self.cy)

    def world(self, lx, lz):
        """Local (x east, z south) to working coordinates."""
        return lx + self.cx, self.cy - lz

    def lonlat(self):
        """A transformer from working coordinates to longitude and latitude."""
        return Transformer.from_crs(self.crs, "EPSG:4326", always_xy=True)

    def bounds_lonlat(self):
        """The terrain square as (west, south, east, north) in degrees."""
        t = self.lonlat()
        h = self.half
        xs, ys = [], []
        for fx in (-1, 0, 1):
            for fy in (-1, 0, 1):
                lon, lat = t.transform(self.cx + fx * h, self.cy + fy * h)
                xs.append(lon)
                ys.append(lat)
        return min(xs), min(ys), max(xs), max(ys)


def square_around(points, crs, margin):
    """The terrain square: the route's bounding box plus `margin` on every side, rounded up to 200 m."""
    xs, ys = [p[0] for p in points], [p[1] for p in points]
    size = math.ceil((max(max(xs) - min(xs), max(ys) - min(ys)) + 2 * margin) / 200) * 200
    cx = round((min(xs) + max(xs)) / 2 / CELL) * CELL
    cy = round((min(ys) + max(ys)) / 2 / CELL) * CELL
    return Frame(crs, cx, cy, size)
