"""The Python validator: the cases shared with the JavaScript validator, and the courses in the repository."""

import copy
import json
from pathlib import Path

import pytest

from tools.coursebuilder.validate import validate_course, validate_folder

ROOT = Path(__file__).resolve().parents[2]
SHARED = json.loads((ROOT / "tests" / "course-cases.json").read_text(encoding="utf-8"))


def _parent(obj, path):
    *keys, last = path.split(".")
    for k in keys:
        obj = obj[int(k)] if isinstance(obj, list) else obj[k]
    return obj, int(last) if isinstance(obj, list) else last


@pytest.mark.parametrize("case", SHARED["cases"], ids=lambda c: c["name"])
def test_shared_case(case):
    base = SHARED["bases"][case["base"]]
    course = copy.deepcopy(base)
    for path, value in case.get("set", {}).items():
        obj, key = _parent(course, path)
        obj[key] = value
    for path in case.get("delete", []):
        obj, key = _parent(course, path)
        del obj[key]
    if "replace" in case:
        course = case["replace"]
    problems = validate_course(course, case.get("id", base["id"]))
    if case["problem"] is None:
        assert problems == []
    else:
        assert any(case["problem"] in p for p in problems), problems


@pytest.mark.parametrize("folder", sorted(p for p in (ROOT / "courses").iterdir() if p.is_dir()), ids=lambda p: p.name)
def test_repository_courses(folder):
    index = json.loads((ROOT / "courses" / "index.json").read_text(encoding="utf-8"))
    assert validate_folder(folder, index) == []


def test_folder_problems_are_reported(tmp_path):
    folder = tmp_path / "my-loop"
    folder.mkdir()
    assert validate_folder(folder) == ["course.json is missing"]
    course = copy.deepcopy(SHARED["bases"]["survey"])
    (folder / "course.json").write_text(json.dumps(course))
    assert validate_folder(folder) == ["terrain.bin is missing"]
    (folder / "terrain.bin").write_bytes(bytes(101 * 101 * 2))
    (folder / "road.json").write_text("[[0, 1, 0], [10, 1, 0], [10, 1, 10], [0, 1, 900]]")
    (folder / "scenery.json").write_text('{"trees": [[1, 2, 3]]}')
    assert validate_folder(folder, index=[]) == [
        "my-loop is not listed in courses/index.json",
        "road.json: point 3 is outside the terrain",
        "scenery.json: trees must be a list of 2-number entries",
    ]
