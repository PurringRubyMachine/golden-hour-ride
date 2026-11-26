"""Reading a route from a GPX file."""

import xml.etree.ElementTree as ET
from pathlib import Path

from . import BuildError


def _local(tag):
    """A tag without its namespace: '{http://www.topografix.com/GPX/1/1}trkpt' -> 'trkpt'."""
    return tag.rsplit("}", 1)[-1]


def read_gpx(path):
    """The route's points as [(lat, lon), ...]: the track points, or the route points if there is no track.

    Several tracks or segments are joined in the order they appear.
    """
    try:
        root = ET.parse(Path(path)).getroot()
    except (OSError, ET.ParseError) as ex:
        raise BuildError(f"could not read {path}: {ex}") from ex
    for kind in ("trkpt", "rtept"):
        points = []
        for el in root.iter():
            if _local(el.tag) == kind:
                try:
                    points.append((float(el.attrib["lat"]), float(el.attrib["lon"])))
                except (KeyError, ValueError) as ex:
                    raise BuildError(f"{path}: a {kind} without a valid lat and lon") from ex
        if points:
            break
    if len(points) < 2:
        raise BuildError(f"{path} has no track or route with at least two points")
    return points
