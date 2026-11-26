"""Building a course: route and DTM in, course folder out."""

import math
from dataclasses import dataclass, field

import numpy as np
from pyproj import CRS, Transformer

from . import BuildError, osm
from .course import write
from .dtm import Dtm
from .frame import choose_crs, crs_name, square_around
from .gpx import read_gpx
from .road import climb, smooth, steepest, surface_heights
from .route import STEP, make_loop

ROAD_EVERY = 3  # keep every third 5 m point: the ride's road line has a point every 15 m


@dataclass
class Options:
    id: str
    name: str
    route: str
    dtm: list
    heights_credit: str
    heights_licence: str
    heights_url: str | None = None
    short_name: str | None = None
    description: str | None = None
    start: float = 0
    scenery_style: str = "plain"
    osm: bool = True
    margin: float = 1300
    close: bool = False
    sheep_above: float | None = None
    stooks_below: float | None = None
    smoke: list = field(default_factory=list)  # [(lat, lon), ...]
    credits: list = field(default_factory=list)  # [{text, licence, url?}, ...]
    courses_dir: str = "courses"
    cache_dir: str = "tools/.cache"


def terrain_at(frame, grid, x, y):
    """The terrain grid's height at a point in working coordinates (bilinear)."""
    c, n = frame.cell, frame.cells
    fx = min(n - 1e-6, max(0.0, (x - (frame.cx - frame.half)) / c))
    fy = min(n - 1e-6, max(0.0, ((frame.cy + frame.half) - y) / c))
    ix, iy = int(fx), int(fy)
    u, v = fx - ix, fy - iy
    g = grid
    return float(
        (g[iy, ix] * (1 - u) + g[iy, ix + 1] * u) * (1 - v) + (g[iy + 1, ix] * (1 - u) + g[iy + 1, ix + 1] * u) * v
    )


def round5(v):
    return float(round(v / 5) * 5)


def build(o, log=print):
    """Build a course. Returns a summary of what was built; raises BuildError if the inputs won't do."""
    latlon = read_gpx(o.route)
    log(f"route: {len(latlon)} points from {o.route}")

    dtm = Dtm(o.dtm)
    try:
        lat = sum(p[0] for p in latlon) / len(latlon)
        lon = sum(p[1] for p in latlon) / len(latlon)
        crs = choose_crs(CRS.from_wkt(dtm.first_crs().to_wkt()), lon, lat)
        dtm.crs = crs.to_wkt()
        log(f"DTM: {len(dtm.sources)} files; working in {crs_name(crs)} ({crs.name})")

        to_xy = Transformer.from_crs("EPSG:4326", crs, always_xy=True)
        line, gap = make_loop([to_xy.transform(lo, la) for la, lo in latlon], close=o.close)
        if gap > STEP:
            log(f"the route's ends were {gap:.0f} m apart; joined")
        frame = square_around(line, crs, o.margin)
        log(f"loop: {len(line) * STEP / 1000:.2f} km; terrain {frame.size} m square, {frame.cells} cells")

        dtm.load_fine(line)
        heights = surface_heights(line, dtm.fine)
        grid, filled = dtm.terrain(frame)
        if filled:
            log(f"terrain: filled {filled} grid points that had no data")
        missing = [k for k, h in enumerate(heights) if h is None]
        if len(missing) == len(heights):
            raise BuildError("the DTM files don't cover the road at all: are they the right area?")
        for k in missing:  # no fine data here (a gap, or water): use the terrain grid
            heights[k] = terrain_at(frame, grid, *line[k])
        if missing:
            log(f"road: {len(missing)} of {len(heights)} points had no fine heights and use the 10 m terrain")
    finally:
        dtm.close()

    heights = smooth(heights)
    up, down = steepest(heights, STEP)
    log(
        f"road: {min(heights):.1f} to {max(heights):.1f} m; climbing {climb(heights):.0f} m; "
        f"steepest {up:.1f}% up, {down:.1f}% down"
    )

    road = []
    for k in range(0, len(line), ROAD_EVERY):
        x, z = frame.local(*line[k])
        road.append([round(x, 2), round(heights[k], 2), round(z, 2)])

    credits = [{"text": o.heights_credit, "licence": o.heights_licence}]
    if o.heights_url:
        credits[0]["url"] = o.heights_url
    credits += o.credits

    course = {
        "format": 1,
        "id": o.id,
        "name": o.name,
        **({"shortName": o.short_name} if o.short_name else {}),
        **({"description": o.description} if o.description else {}),
        "kind": "survey",
        "loop": True,
        "start": o.start,
        "origin": {"crs": crs_name(crs), "x": frame.cx, "y": frame.cy},
        "terrain": {"file": "terrain.bin", "size": frame.size, "cells": frame.cells},
        "road": "road.json",
    }

    scenery = None
    options = {}
    if o.scenery_style == "pastoral-1800s":
        options["sheepAbove"] = o.sheep_above if o.sheep_above is not None else round5(np.percentile(heights, 65))
        options["stooksBelow"] = o.stooks_below if o.stooks_below is not None else round5(np.percentile(heights, 35))
    if o.smoke:
        options["smoke"] = [[round(v, 1) for v in frame.local(*to_xy.transform(lo, la))] for la, lo in o.smoke]
    if o.osm:
        log("scenery: fetching OpenStreetMap features (cached after the first time)")
        scenery = osm.scenery(frame, [(p[0], p[2]) for p in road], o.cache_dir)
        log(
            f"scenery: {len(scenery['buildings'])} buildings, {len(scenery['trees'])} single trees, "
            f"{len(scenery['lines'])} hedge and wall pieces"
        )
        credits.append(dict(osm.CREDIT))
    if scenery is not None or o.scenery_style != "plain" or options:
        course["scenery"] = {
            **({"file": "scenery.json"} if scenery is not None else {}),
            "style": o.scenery_style,
            "options": options,
        }
    course["credits"] = credits

    problems = write(o.courses_dir, course, grid, road, scenery)
    if problems:
        raise BuildError("the course was written but doesn't validate: " + "; ".join(problems))
    km = sum(math.dist((a[0], a[2]), (b[0], b[2])) for a, b in zip(road, road[1:] + road[:1])) / 1000
    log(f"wrote {o.courses_dir}/{o.id}/: {km:.1f} km")
    return {"course": course, "road": road, "heights": heights, "line": line, "frame": frame}
