"""Scenery from OpenStreetMap: buildings, single trees, woodland, hedges and walls.

Fetched from the Overpass API for the terrain square and cached, so a rebuild doesn't fetch again.
OpenStreetMap data is © OpenStreetMap contributors, under the ODbL.
"""

import base64
import hashlib
import json
import math
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

import numpy as np

from . import BuildError

OVERPASS = "https://overpass-api.de/api/interpreter"
USER_AGENT = "golden-hour-ride-coursebuilder"
CREDIT = {
    "text": "Buildings, woods and hedges © OpenStreetMap contributors.",
    "licence": "ODbL-1.0",
    "url": "https://www.openstreetmap.org/copyright",
}

SMALL_BUILDINGS = {"garage", "garages", "shed", "hut", "carport", "roof", "greenhouse"}


def query(south, west, north, east):
    box = f"({south:.6f},{west:.6f},{north:.6f},{east:.6f})"
    return f"""[out:json][timeout:180];
(
  way["building"]{box};
  node["natural"="tree"]{box};
  way["natural"="wood"]{box};
  way["landuse"="forest"]{box};
  relation["natural"="wood"]{box};
  relation["landuse"="forest"]{box};
  way["barrier"~"^(hedge|wall|retaining_wall)$"]{box};
);
out geom;"""


def fetch(q, cache_dir):
    """Overpass's answer to a query, from the cache if this query has been asked before."""
    cache = Path(cache_dir) / f"overpass-{hashlib.sha256(q.encode()).hexdigest()[:16]}.json"
    if cache.exists():
        return json.loads(cache.read_text(encoding="utf-8"))
    body = urllib.parse.urlencode({"data": q}).encode()
    request = urllib.request.Request(OVERPASS, data=body, headers={"User-Agent": USER_AGENT})
    for attempt in range(5):
        try:
            with urllib.request.urlopen(request, timeout=240) as r:
                data = r.read()
            break
        except urllib.error.HTTPError as ex:  # busy: wait and try again
            if ex.code not in (429, 502, 503, 504) or attempt == 4:
                raise BuildError(f"OpenStreetMap (Overpass) refused the request: {ex}") from ex
            time.sleep(15 * (attempt + 1))
        except urllib.error.URLError as ex:
            raise BuildError(f"could not reach OpenStreetMap (Overpass): {ex.reason}. Use --no-osm to skip") from ex
    cache.parent.mkdir(parents=True, exist_ok=True)
    cache.write_bytes(data)
    return json.loads(data)


def _height(tags):
    """A building's height in metres, from its tags or its kind."""
    try:
        return max(2.5, float(str(tags.get("height", "")).replace("m", "").strip()))
    except ValueError:
        pass
    try:
        return max(2.5, float(tags["building:levels"]) * 3)
    except (KeyError, ValueError):
        pass
    if tags.get("building") == "church" or tags.get("amenity") == "place_of_worship":
        return 13.0
    if tags.get("building") in SMALL_BUILDINGS:
        return 2.6
    return 5.6


def _box(pts):
    """The smallest rectangle around a footprint, trying each wall's direction: (x, z, width, depth, angle)."""
    best = None
    for (x1, z1), (x2, z2) in zip(pts, pts[1:]):
        length = math.hypot(x2 - x1, z2 - z1)
        if length < 0.5:
            continue
        ux, uz = (x2 - x1) / length, (z2 - z1) / length
        us = [x * ux + z * uz for x, z in pts]
        vs = [-x * uz + z * ux for x, z in pts]
        w, d = max(us) - min(us), max(vs) - min(vs)
        if best is None or w * d < best[0]:
            cu, cv = (max(us) + min(us)) / 2, (max(vs) + min(vs)) / 2
            best = (w * d, cu * ux - cv * uz, cu * uz + cv * ux, w, d, math.atan2(uz, ux))
    return best and best[1:]


class _Road:
    """Distance from the road line, for many points at once."""

    def __init__(self, road_xz):
        self.xz = np.asarray(road_xz, dtype=float)

    def dist(self, x, z):
        return float(np.sqrt(((self.xz[:, 0] - x) ** 2 + (self.xz[:, 1] - z) ** 2).min()))


def convert(elements, frame, road_xz):
    """OpenStreetMap elements to the course's scenery: buildings, trees, lines (hedges and walls) and woods.

    road_xz is the road line in local metres. Things you'd never see from the road, or that overlap it, are left
    out. The format of each entry is in docs/refactor-plan.md ("Course format, version 1").
    """
    to_xy = frame.lonlat()
    half = frame.half
    road = _Road(road_xz)

    def local(lat, lon):
        x, y = to_xy.transform(lon, lat, direction="INVERSE")
        return frame.local(x, y)

    def inside(x, z, m=0):
        return abs(x) < half - m and abs(z) < half - m

    def ring(geom):
        return [local(p["lat"], p["lon"]) for p in geom]

    buildings, trees, lines, woods, holes = [], [], [], [], []
    for e in elements:
        t = e.get("tags", {})
        if e["type"] == "node":
            if t.get("natural") == "tree":
                x, z = local(e["lat"], e["lon"])
                if inside(x, z, 20) and road.dist(x, z) > 4.5:
                    trees.append([round(x, 1), round(z, 1)])
        elif e["type"] == "way" and "geometry" in e:
            pts = ring(e["geometry"])
            if t.get("building") and len(pts) >= 4:
                b = _box(pts)
                if not b:
                    continue
                x, z, w, d, ang = b
                if w < d:
                    w, d, ang = d, w, ang + math.pi / 2
                if not inside(x, z, 40) or w > 90 or w < 2 or d < 2:
                    continue
                rd = road.dist(x, z)
                if rd > 700 or rd < d / 2 + 4.5:
                    continue
                h = _height(t)
                pitched = 0 if (h < 3.5 or d > 14) else 1
                buildings.append(
                    [round(x, 1), round(z, 1), round(w, 1), round(d, 1), round(ang, 3), round(h, 1), pitched]
                )
            elif t.get("natural") == "wood" or t.get("landuse") == "forest":
                if len(pts) >= 4:
                    woods.append(pts)
            elif t.get("barrier") in ("hedge", "wall", "retaining_wall"):
                kind = 0 if t["barrier"] == "hedge" else 1
                for (x1, z1), (x2, z2) in zip(pts, pts[1:]):
                    n = max(1, math.ceil(math.hypot(x2 - x1, z2 - z1) / 6))
                    for k in range(n):
                        ax, az = x1 + (x2 - x1) * k / n, z1 + (z2 - z1) * k / n
                        bx, bz = x1 + (x2 - x1) * (k + 1) / n, z1 + (z2 - z1) * (k + 1) / n
                        mx, mz = (ax + bx) / 2, (az + bz) / 2
                        if inside(mx, mz, 20) and 4.4 < road.dist(mx, mz) < 400:
                            lines.append([round(ax, 1), round(az, 1), round(bx, 1), round(bz, 1), kind])
        elif e["type"] == "relation" and (t.get("natural") == "wood" or t.get("landuse") == "forest"):
            for m in e.get("members", []):
                if m.get("type") == "way" and len(m.get("geometry") or []) >= 3:
                    (holes if m.get("role") == "inner" else woods).append(ring(m["geometry"]))
    return {"buildings": buildings, "trees": trees, "lines": lines, "woods": woods_mask(frame, woods, holes)}


def woods_mask(frame, woods, holes):
    """Woodland as one bit per terrain grid point (row 0 at the north edge), base64-encoded."""
    cells, size, half = frame.cells, frame.size, frame.half
    w = cells + 1
    mask = bytearray(w * w)

    def fill(poly, val):
        if poly[0] != poly[-1]:
            poly = poly + [poly[0]]
        zs = [p[1] for p in poly]
        top = max(0, math.ceil((min(zs) + half) / size * cells))
        bottom = min(cells, math.floor((max(zs) + half) / size * cells))
        for iz in range(top, bottom + 1):
            z = -half + iz * size / cells
            xs = sorted(
                x1 + (z - z1) / (z2 - z1) * (x2 - x1)
                for (x1, z1), (x2, z2) in zip(poly, poly[1:])
                if (z1 <= z < z2) or (z2 <= z < z1)
            )
            for a, b in zip(xs[::2], xs[1::2]):
                left = max(0, math.ceil((a + half) / size * cells))
                right = min(cells, math.floor((b + half) / size * cells))
                for ix in range(left, right + 1):
                    mask[iz * w + ix] = val

    for p in woods:
        fill(p, 1)
    for p in holes:
        fill(p, 0)
    bits = bytearray((len(mask) + 7) // 8)
    for i, v in enumerate(mask):
        if v:
            bits[i >> 3] |= 1 << (i & 7)
    return base64.b64encode(bytes(bits)).decode()


def scenery(frame, road_xz, cache_dir):
    """Fetch and convert the OpenStreetMap scenery for a course. Returns it, and how current the map data was."""
    west, south, east, north = frame.bounds_lonlat()
    data = fetch(query(south, west, north, east), cache_dir)
    return convert(data.get("elements", []), frame, road_xz), data.get("osm3s", {}).get("timestamp_osm_base")
