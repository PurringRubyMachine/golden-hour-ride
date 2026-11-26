"""Writing a course folder and listing it in courses/index.json."""

import json
from pathlib import Path

import numpy as np

from . import BuildError
from .validate import validate_folder

WIDTH = 120  # the repository's line length (Prettier's printWidth)


def dumps(value, indent=0, key_width=0):
    """JSON laid out as Prettier lays it out: objects one key per line, arrays on one line when they fit."""
    pad = " " * indent
    if isinstance(value, dict):
        if not value:
            return "{}"
        items = [f"{pad}  {json.dumps(k, ensure_ascii=False)}: " for k in value]
        body = [item + dumps(v, indent + 2, len(item)) for item, v in zip(items, value.values())]
        return "{\n" + ",\n".join(body) + "\n" + pad + "}"
    if isinstance(value, list):
        flat = json.dumps(value, ensure_ascii=False, separators=(", ", ": "))
        if "\n" not in flat and key_width + len(flat) + 1 <= WIDTH and not any(isinstance(v, dict) for v in value):
            return flat
        body = [pad + "  " + dumps(v, indent + 2, indent + 2) for v in value]
        return "[\n" + ",\n".join(body) + "\n" + pad + "]"
    return json.dumps(value, ensure_ascii=False)


def write_json(path, value, pretty=True):
    text = dumps(value) if pretty else json.dumps(value, ensure_ascii=False, separators=(",", ":"))
    Path(path).write_text(text + "\n", encoding="utf-8")


def quantise(heights):
    """Terrain heights as little-endian uint16 between their lowest and highest, plus those two heights."""
    lo, hi = float(np.min(heights)), float(np.max(heights))
    if hi - lo < 0.01:
        hi = lo + 0.01  # flat ground: keep min below max
    q = np.round((heights - lo) / (hi - lo) * 65535).astype("<u2")
    return q.tobytes(), lo, hi


def write(courses_dir, course, terrain_heights, road, scenery=None):
    """Write courses/<id>/ and update courses/index.json. Returns the problems the validator finds (none, normally).

    course is the course.json contents, without the terrain's min and max, which come from the heights.
    """
    courses_dir = Path(courses_dir)
    folder = courses_dir / course["id"]
    folder.mkdir(parents=True, exist_ok=True)
    data, lo, hi = quantise(terrain_heights)
    course["terrain"].update(min=lo, max=hi)
    (folder / course["terrain"]["file"]).write_bytes(data)
    write_json(folder / course["road"], road, pretty=False)
    if scenery is not None:
        write_json(folder / course["scenery"]["file"], scenery, pretty=False)
    write_json(folder / "course.json", course)

    index_path = courses_dir / "index.json"
    try:
        index = json.loads(index_path.read_text(encoding="utf-8")) if index_path.exists() else []
    except json.JSONDecodeError as ex:
        raise BuildError(f"{index_path} is not valid JSON: {ex}") from ex
    entry = {
        "id": course["id"],
        "name": course["name"],
        **({"shortName": course["shortName"]} if "shortName" in course else {}),
        "lengthKm": round(_length(road) / 1000, 1),
        "climbM": round(_climb(road)),
    }
    at = next((i for i, e in enumerate(index) if e.get("id") == course["id"]), None)
    if at is None:
        index.append(entry)
    else:
        index[at] = entry
    write_json(index_path, index)
    return validate_folder(folder, index)


def _length(road):
    n = len(road)
    return sum(
        ((road[(k + 1) % n][0] - p[0]) ** 2 + (road[(k + 1) % n][2] - p[2]) ** 2) ** 0.5 for k, p in enumerate(road)
    )


def _climb(road):
    n = len(road)
    return sum(max(0.0, road[(k + 1) % n][1] - p[1]) for k, p in enumerate(road))
