"""Checks a course against format 1: the Python twin of src/course/validate.js.

The two give the same answers and messages; tests/course-cases.json is run by both test suites to keep them so.
Each function returns a list of problems, empty when all is well.
"""

import json
import math
import re
from pathlib import Path

FORMAT = 1
GENERATORS = ["valley"]
SCENERY_STYLES = ["pastoral-1800s", "plain"]
_BASE64 = re.compile(r"(?:[A-Za-z0-9+/]{4})*(?:[A-Za-z0-9+/]{2}==|[A-Za-z0-9+/]{3}=)?")
_ID = re.compile(r"[a-z0-9][a-z0-9-]*")


def _num(v):
    return isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(v)


def _int(v):
    return _num(v) and float(v).is_integer()


def _text(v):
    return isinstance(v, str) and v.strip() != ""


def _obj(v):
    return isinstance(v, dict)


def _point(p, n):
    return isinstance(p, list) and len(p) == n and all(_num(v) for v in p)


def _quote(s):
    """A string the way JavaScript's template literals print it."""
    return s if isinstance(s, str) else json.dumps(s)


def validate_course(c, id):
    """course.json. id is the folder name, which the course's own id must match."""
    if not _obj(c):
        return ["course.json must be an object"]
    bad = []

    def need(ok, problem):
        if not ok:
            bad.append(problem)

    need(c.get("format") == FORMAT and _int(c.get("format")), f"format must be {FORMAT}")
    need(c.get("id") == id, f'id must be "{_quote(id)}", the name of the course\'s folder')
    need(isinstance(id, str) and _ID.fullmatch(id), "id must be lower-case letters, digits and hyphens")
    need(_text(c.get("name")), "name is required")
    need("shortName" not in c or _text(c["shortName"]), "shortName must be text")
    need("description" not in c or isinstance(c["description"], str), "description must be text")
    need(c.get("loop") is True, "loop must be true: format 1 supports loops only")
    need("start" not in c or (_num(c["start"]) and c["start"] >= 0), "start must be a distance in metres, 0 or more")

    credits = c.get("credits")
    need(isinstance(credits, list), "credits must be a list")
    if isinstance(credits, list):
        for i, cr in enumerate(credits):
            need(_obj(cr) and _text(cr.get("text")), f"credits[{i}].text is required")
            need(_obj(cr) and _text(cr.get("licence")), f"credits[{i}].licence is required")
            need(not _obj(cr) or "url" not in cr or _text(cr["url"]), f"credits[{i}].url must be text")

    kind = c.get("kind")
    if kind == "procedural":
        need(c.get("generator") in GENERATORS, f"generator must be one of: {', '.join(GENERATORS)}")
    elif kind == "survey":
        need(
            not isinstance(credits, list) or len(credits) > 0,  # (a missing list is reported above)
            "credits must name the sources of the data and their licences",
        )
        o = c.get("origin")
        need(_obj(o) and _text(o.get("crs")) and _num(o.get("x")) and _num(o.get("y")), "origin needs crs, x and y")
        t = c.get("terrain")
        if not _obj(t):
            bad.append("terrain is required")
        else:
            need(_text(t.get("file")), "terrain.file is required")
            need(_num(t.get("size")) and t["size"] > 0, "terrain.size must be a width in metres")
            need(_int(t.get("cells")) and t["cells"] > 0, "terrain.cells must be a whole number")
            need(
                _num(t.get("min")) and _num(t.get("max")) and t["min"] < t["max"],
                "terrain.min and terrain.max must be heights, min below max",
            )
        need(_text(c.get("road")), "road must name the road file")
        if "scenery" in c:
            s = c["scenery"]
            if not _obj(s):
                bad.append("scenery must be an object")
            else:
                need("file" not in s or _text(s["file"]), "scenery.file must be text")
                need(s.get("style") in SCENERY_STYLES, f"scenery.style must be one of: {', '.join(SCENERY_STYLES)}")
                op = s.get("options")
                op = {} if op is None else op
                need(_obj(op), "scenery.options must be an object")
                if _obj(op):
                    need(
                        "sheepAbove" not in op or _num(op["sheepAbove"]), "scenery.options.sheepAbove must be a height"
                    )
                    need(
                        "stooksBelow" not in op or _num(op["stooksBelow"]),
                        "scenery.options.stooksBelow must be a height",
                    )
                    smoke = op.get("smoke")
                    need(
                        "smoke" not in op or (isinstance(smoke, list) and all(_point(p, 2) for p in smoke)),
                        "scenery.options.smoke must be a list of [x, z] points",
                    )
    else:
        bad.append('kind must be "survey" or "procedural"')
    return bad


def validate_terrain(c, byte_length):
    """terrain.bin: (cells + 1)² little-endian uint16 heights."""
    want = (c["terrain"]["cells"] + 1) ** 2 * 2
    return [] if byte_length == want else [f"{c['terrain']['file']} is {byte_length} bytes; {want} expected"]


def validate_road(c, road):
    """road.json: [[x, y, z], ...] in metres, inside the terrain."""
    if not isinstance(road, list) or len(road) < 4:
        return [f"{c['road']} must list at least 4 points"]
    half = c["terrain"]["size"] / 2
    for i, p in enumerate(road):
        if not _point(p, 3):
            return [f"{c['road']}: point {i} must be [x, y, z] in metres"]
    for i, (x, _, z) in enumerate(road):
        if abs(x) > half or abs(z) > half:
            return [f"{c['road']}: point {i} is outside the terrain"]
    return []


def validate_scenery(c, sc):
    """scenery.json: buildings, trees, lines and the woodland mask, all optional."""
    name = c["scenery"]["file"]
    if not _obj(sc):
        return [f"{name} must be an object"]
    bad = []
    for key, n in (("buildings", 7), ("trees", 2), ("lines", 5)):
        if key in sc and not (isinstance(sc[key], list) and all(_point(p, n) for p in sc[key])):
            bad.append(f"{name}: {key} must be a list of {n}-number entries")
    if "woods" in sc:
        chars = 4 * math.ceil(math.ceil((c["terrain"]["cells"] + 1) ** 2 / 8) / 3)
        w = sc["woods"]
        if not isinstance(w, str) or (w != "" and (len(w) != chars or not _BASE64.fullmatch(w))):
            bad.append(f"{name}: woods must be {chars} characters of base64 (one bit per terrain point)")
    return bad


def validate_folder(folder, index=None):
    """Every check on a course folder, plus its entry in courses/index.json when the index is given."""
    folder = Path(folder)
    id = folder.name

    def load(name):
        try:
            return json.loads((folder / name).read_text(encoding="utf-8"))
        except FileNotFoundError:
            raise _Missing(f"{name} is missing") from None
        except json.JSONDecodeError as ex:
            raise _Missing(f"{name} is not valid JSON: {ex}") from None

    try:
        c = load("course.json")
        bad = validate_course(c, id)
        if bad:
            return bad
        if index is not None:
            entry = next((e for e in index if e.get("id") == id), None)
            if entry is None:
                bad.append(f"{id} is not listed in courses/index.json")
            elif entry.get("name") != c["name"] or entry.get("shortName") != c.get("shortName"):
                bad.append(f"the name in courses/index.json doesn't match {id}/course.json")
        if c["kind"] == "survey":
            terrain = folder / c["terrain"]["file"]
            if not terrain.exists():
                return bad + [f"{c['terrain']['file']} is missing"]
            bad += validate_terrain(c, terrain.stat().st_size)
            bad += validate_road(c, load(c["road"]))
            if c.get("scenery", {}).get("file"):
                bad += validate_scenery(c, load(c["scenery"]["file"]))
        return bad
    except _Missing as ex:
        return [str(ex)]


class _Missing(Exception):
    pass
