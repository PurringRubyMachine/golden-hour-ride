"""Cleaning a route into an evenly spaced loop, in projected metres."""

import math

from . import BuildError

STEP = 5.0  # metres between resampled points
MAX_GAP = 50.0  # a loop's ends may be this far apart; further needs --close


def remove_spurs(points, look=600.0, leave=20.0, back=8.0):
    """Cut out-and-back spurs, such as a router's detour to touch a waypoint.

    From each point, look up to `look` metres ahead. If the path goes at least `leave` metres and then comes back
    within `back` metres of the point, jump to where it came back.
    """
    out, i = [], 0
    while i < len(points):
        out.append(points[i])
        skip, run, j = -1, 0.0, i + 1
        while j < len(points) and run < look:
            run += math.dist(points[j - 1], points[j])
            if run > leave and math.dist(points[i], points[j]) < back:
                skip = j
            j += 1
        i = skip + 1 if skip > 0 else i + 1
    return out


def drop_repeats(points):
    """Remove points that sit on the one before (GPS recorders repeat points while stopped)."""
    out = [points[0]]
    for p in points[1:]:
        if math.dist(p, out[-1]) > 0.01:
            out.append(p)
    return out


def resample(points, step=STEP):
    """Points every `step` metres along the line, starting at its first point."""
    line, carry = [points[0]], 0.0
    for a, b in zip(points, points[1:]):
        length = math.dist(a, b)
        if length == 0:
            continue
        d = step - carry
        while d <= length:
            t = d / length
            line.append((a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t))
            d += step
        carry = length - (d - step)
    return line


def make_loop(points, close=False, step=STEP):
    """The route as a closed loop of points `step` metres apart, without repeating the first point at the end.

    Format 1 courses are loops. If the ends are more than MAX_GAP apart the route is refused unless close=True, which
    joins them with a straight line.
    """
    points = drop_repeats(remove_spurs(drop_repeats(points)))
    if len(points) < 3:
        raise BuildError("the route has fewer than three distinct points")
    gap = math.dist(points[0], points[-1])
    if gap > MAX_GAP and not close:
        raise BuildError(
            f"the route's ends are {gap:.0f} m apart. Courses are loops: finish where you started, or pass --close "
            "to join the ends with a straight line"
        )
    line = resample(points + [points[0]], step)
    if math.dist(line[-1], line[0]) < step / 2:
        line.pop()
    if len(line) < 20:
        raise BuildError(f"the loop is only {len(line) * step:.0f} m long")
    return line, gap
