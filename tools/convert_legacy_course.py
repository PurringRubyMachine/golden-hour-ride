"""Convert a course from the old JavaScript files to course format 1.

    python3 tools/convert_legacy_course.py leckhampton

Reads assets/<id>.js and assets/<id>_osm.js (which set window.RIDE_COURSES) and writes courses/<id>/.
Numbers are copied exactly, so the converted course rides the same. Standard library only.
Afterwards run  npx prettier --write courses  so course.json is laid out the way the repository checks.

This is a one-off for the courses that existed before format 1. It goes away with the old build scripts once
the course builder (tools/coursebuilder) can rebuild them; see docs/refactor-plan.md, phase 4.
"""

import base64
import json
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# What the old files didn't hold: these values were fixed in the app's code.
LEGACY = {
    "leckhampton": {
        "shortName": "Leckhampton",
        "description": "A loop over the Cotswold scarp above Cheltenham, past the old quarries on Leckhampton Hill.",
        "start": 850,  # on the lane about 150 m below where the hill steepens, not out in the vale
        "crs": "EPSG:27700",  # British National Grid
        "style": "pastoral-1800s",
        "options": {"sheepAbove": 175, "stooksBelow": 150},
        # The old credit lines, split up so each source carries its licence. Joined with spaces they read as before.
        "credits": [
            {
                "text": "Route © OpenStreetMap contributors.",
                "licence": "ODbL-1.0",
                "url": "https://www.openstreetmap.org/copyright",
            },
            {
                "text": "Heights: Environment Agency LiDAR, Open Government Licence.",
                "licence": "OGL-UK-3.0",
                "url": "https://environment.data.gov.uk/survey",
            },
            {
                "text": "Buildings, woods and hedges © OpenStreetMap contributors.",
                "licence": "ODbL-1.0",
                "url": "https://www.openstreetmap.org/copyright",
            },
        ],
    },
}


def read_js(path, prefix):
    """The JSON object assigned in a line starting with prefix."""
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.startswith(prefix):
            return json.loads(line[len(prefix) :].rstrip().rstrip(";"))
    raise SystemExit(f"{path}: no line starting {prefix!r}")


def climb(road):
    """Total climbing round the loop, in metres."""
    ys = [p[1] for p in road]
    return sum(max(0.0, b - a) for a, b in zip(ys, ys[1:] + ys[:1]))


def length(road):
    """Length of the loop along the road points, in metres."""
    return sum(math.dist((a[0], a[2]), (b[0], b[2])) for a, b in zip(road, road[1:] + road[:1]))


def write_json(path, data, indent=None):
    text = json.dumps(data, ensure_ascii=False, indent=indent, separators=None if indent else (",", ":"))
    path.write_text(text + "\n", encoding="utf-8")


def main(course_id):
    extra = LEGACY[course_id]
    old = read_js(ROOT / "assets" / f"{course_id}.js", f"window.RIDE_COURSES.{course_id} = ")
    osm = read_js(ROOT / "assets" / f"{course_id}_osm.js", f"window.RIDE_COURSES.{course_id}.osm = ")

    out = ROOT / "courses" / course_id
    out.mkdir(parents=True, exist_ok=True)

    cells = old["cells"]
    heights = base64.b64decode(old["dem"])
    if len(heights) != (cells + 1) ** 2 * 2:
        raise SystemExit(f"terrain is {len(heights)} bytes, expected {(cells + 1) ** 2 * 2}")
    (out / "terrain.bin").write_bytes(heights)  # already little-endian uint16, row 0 at the north edge

    road = old["road"]
    write_json(out / "road.json", road)
    write_json(out / "scenery.json", {k: osm[k] for k in ("buildings", "trees", "lines", "woods")})

    options = dict(extra["options"])
    if "quarry" in old:
        options["smoke"] = [old["quarry"]]
    course = {
        "format": 1,
        "id": course_id,
        "name": old["name"],
        "shortName": extra["shortName"],
        "description": extra["description"],
        "kind": "survey",
        "loop": True,
        "start": extra["start"],
        "origin": {"crs": extra["crs"], "x": old["origin"][0], "y": old["origin"][1]},
        "terrain": {
            "file": "terrain.bin",
            "size": old["size"],
            "cells": cells,
            "min": old["demMin"],
            "max": old["demMax"],
        },
        "road": "road.json",
        "scenery": {"file": "scenery.json", "style": extra["style"], "options": options},
        "credits": extra["credits"],
    }
    write_json(out / "course.json", course, indent=2)

    # List it in courses/index.json, replacing any earlier entry.
    index_path = ROOT / "courses" / "index.json"
    index = json.loads(index_path.read_text(encoding="utf-8")) if index_path.exists() else []
    entry = {
        "id": course_id,
        "name": old["name"],
        "shortName": extra["shortName"],
        "lengthKm": round(length(road) / 1000, 1),
        "climbM": round(climb(road)),
    }
    index = [e for e in index if e["id"] != course_id] + [entry]
    write_json(index_path, index, indent=2)
    print(f"wrote {out.relative_to(ROOT)}: {entry['lengthKm']} km, {entry['climbM']} m climbing")


if __name__ == "__main__":
    if len(sys.argv) != 2 or sys.argv[1] not in LEGACY:
        raise SystemExit(f"usage: {sys.argv[0]} {{{','.join(LEGACY)}}}")
    main(sys.argv[1])
