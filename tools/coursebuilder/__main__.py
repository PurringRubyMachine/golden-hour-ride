"""The course builder's command line: python -m tools.coursebuilder {build,validate,fetch-ea} ..."""

import argparse
import json
import sys
from pathlib import Path

from . import BuildError
from .validate import validate_folder


def _latlon(text):
    try:
        lat, lon = (float(v) for v in text.split(","))
    except ValueError:
        raise argparse.ArgumentTypeError(f"expected LAT,LON such as 51.8642,-2.0787, not {text!r}") from None
    return lat, lon


def _metres(text):
    """A distance or height: whole numbers stay whole, so course.json says 850, not 850.0."""
    v = float(text)
    return int(v) if v.is_integer() else v


def _credit(text):
    parts = text.split("|")
    if len(parts) not in (2, 3) or not all(p.strip() for p in parts):
        raise argparse.ArgumentTypeError(f'expected "TEXT|LICENCE" or "TEXT|LICENCE|URL", not {text!r}')
    credit = {"text": parts[0].strip(), "licence": parts[1].strip()}
    if len(parts) == 3:
        credit["url"] = parts[2].strip()
    return credit


def parser():
    p = argparse.ArgumentParser(prog="python -m tools.coursebuilder", description=__doc__)
    sub = p.add_subparsers(dest="command", required=True)

    b = sub.add_parser("build", help="build a course from a GPX route and DTM files")
    b.add_argument("--id", required=True, help="folder name: lower-case letters, digits and hyphens")
    b.add_argument("--name", required=True, help='the course\'s name, such as "Leckhampton Hill loop"')
    b.add_argument("--short-name", help="a short name for the course button and ride log")
    b.add_argument("--description", help="a sentence about the course")
    b.add_argument("--route", required=True, help="the route as a GPX file (a track, or a route)")
    b.add_argument("--dtm", required=True, nargs="+", help="DTM files, or folders of them, in any coordinate system")
    b.add_argument("--heights-credit", required=True, help='credit for the DTM, such as "Heights: ... LiDAR"')
    b.add_argument("--heights-licence", required=True, help="the DTM's licence, such as OGL-UK-3.0")
    b.add_argument("--heights-url", help="where the DTM comes from")
    b.add_argument(
        "--credit",
        type=_credit,
        action="append",
        default=[],
        metavar='"TEXT|LICENCE[|URL]"',
        help="another source to credit, such as where the route came from (repeatable)",
    )
    b.add_argument("--scenery-style", choices=["plain", "pastoral-1800s"], default="plain")
    b.add_argument("--sheep-above", type=_metres, metavar="METRES", help="pastoral: sheep graze above this height")
    b.add_argument(
        "--stooks-below", type=_metres, metavar="METRES", help="pastoral: hay stooks stand below this height"
    )
    b.add_argument(
        "--smoke",
        type=_latlon,
        action="append",
        default=[],
        metavar="LAT,LON",
        help="smoke rises from the steepest ground near here, such as a quarry (repeatable)",
    )
    b.add_argument(
        "--osm",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="buildings, woods and hedges from OpenStreetMap (default: on)",
    )
    b.add_argument("--margin", type=float, default=1300, metavar="METRES", help="terrain around the route (1300)")
    b.add_argument("--close", action="store_true", help="join the route's ends if they're more than 50 m apart")
    b.add_argument("--start", type=_metres, default=0, metavar="METRES", help="where riders begin, along the loop")
    b.add_argument("--courses-dir", default="courses", help=argparse.SUPPRESS)
    b.add_argument("--cache-dir", default="tools/.cache", help=argparse.SUPPRESS)

    v = sub.add_parser("validate", help="check course folders against the format")
    v.add_argument("folders", nargs="*", help="course folders (default: every folder in courses/)")

    e = sub.add_parser("fetch-ea", help="download Environment Agency LiDAR for a route in England")
    e.add_argument("--route", required=True, help="the route as a GPX file")
    e.add_argument("--out", required=True, help="folder for the tiles; pass it to build --dtm")
    e.add_argument("--margin", type=float, default=1300, metavar="METRES", help="terrain around the route (1300)")
    return p


def cmd_build(a):
    from .build import Options, build  # imports rasterio, which only build needs

    fields = {k: v for k, v in vars(a).items() if k != "command" and v is not None}
    fields["credits"] = fields.pop("credit")
    build(Options(**fields))
    return 0


def cmd_validate(a):
    folders = [Path(f) for f in a.folders] or sorted(f for f in Path("courses").iterdir() if f.is_dir())
    failed = 0
    for folder in folders:
        index_path = folder.parent / "index.json"
        index = json.loads(index_path.read_text(encoding="utf-8")) if index_path.exists() else None
        problems = validate_folder(folder, index)
        print(f"{folder}: {'ok' if not problems else 'problems'}")
        for problem in problems:
            print(f"  - {problem}")
        failed += bool(problems)
    return 1 if failed else 0


def cmd_fetch_ea(a):
    from . import ea
    from .gpx import read_gpx

    ea.fetch(read_gpx(a.route), a.out, a.margin)
    print("Build with:  --dtm", a.out, " ".join(f'"{v}"' if " " in v else v for v in ea.CREDIT_ARGS))
    return 0


def main(argv=None):
    a = parser().parse_args(argv)
    try:
        return {"build": cmd_build, "validate": cmd_validate, "fetch-ea": cmd_fetch_ea}[a.command](a)
    except BuildError as ex:
        print(f"error: {ex}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
