"""Road heights: the surface across the road, smoothed round the loop."""

import math

ACROSS = range(-7, 8)  # metres either side of the centre line to look for the road surface


def normals(line):
    """The unit vector to the left of the direction of travel at each point of a loop."""
    n = len(line)
    out = []
    for k in range(n):
        (ax, ay), (bx, by) = line[k - 1], line[(k + 1) % n]
        length = math.hypot(bx - ax, by - ay) or 1.0
        out.append((-(by - ay) / length, (bx - ax) / length))
    return out


def surface_heights(line, height_at):
    """The road surface at each point: the flattest spot across the road, preferring the centre.

    LiDAR heights at a road's centre line can catch a bank, a hedge or a cutting's side where the line drifts off
    the tarmac, so look up to 7 m either side for the spot where the ground is flattest across the road.
    height_at(x, y) returns a height or None. Returns heights, with None where nothing was found.
    """
    out = []
    for (x, y), (nx, ny) in zip(line, normals(line)):
        best = None
        for off in ACROSS:
            h0 = height_at(x + nx * (off - 1.5), y + ny * (off - 1.5))
            h1 = height_at(x + nx * off, y + ny * off)
            h2 = height_at(x + nx * (off + 1.5), y + ny * (off + 1.5))
            if h0 is None or h1 is None or h2 is None:
                continue
            flat = abs(h2 - h0) + abs(off) * 0.02
            if best is None or flat < best[0]:
                best = (flat, h1)
        out.append(best[1] if best else None)
    return out


def across_bridges(line, heights, bridges, near=10, angle=30):
    """Heights drawn straight across bridges, instead of dipping to the ground beneath them.

    A point counts as on a bridge when it is within `near` metres of one and the bridge runs the same way as the road
    there (within `angle` degrees), so a road that passes under a bridge is left alone. Each run of bridge points,
    plus one point each side for the abutments, is replaced by a straight line between the heights just beyond it.
    Returns the new heights and how many bridges were crossed.
    """
    n = len(line)
    segs = [(a, b) for bridge in bridges for a, b in zip(bridge, bridge[1:]) if math.dist(a, b) > 0.1]
    if not segs:
        return list(heights), 0
    cos_max = math.cos(math.radians(angle))
    cell = 50.0  # a grid of the segments, so each point only checks the bridges near it
    grid = {}
    for seg in segs:
        (ax, ay), (bx, by) = seg
        for i in range(math.floor((min(ax, bx) - near) / cell), math.floor((max(ax, bx) + near) / cell) + 1):
            for j in range(math.floor((min(ay, by) - near) / cell), math.floor((max(ay, by) + near) / cell) + 1):
                grid.setdefault((i, j), []).append(seg)
    on = [False] * n
    for k, ((x, y), (nx, ny)) in enumerate(zip(line, normals(line))):
        tx, ty = ny, -nx  # direction of travel
        for (ax, ay), (bx, by) in grid.get((math.floor(x / cell), math.floor(y / cell)), ()):
            dx, dy = bx - ax, by - ay
            length = math.hypot(dx, dy)
            t = max(0.0, min(1.0, ((x - ax) * dx + (y - ay) * dy) / (length * length)))
            if math.hypot(ax + t * dx - x, ay + t * dy - y) <= near and abs(tx * dx + ty * dy) / length >= cos_max:
                on[k] = True
                break
    if all(on):
        return list(heights), 0  # a loop entirely on bridges: nothing to measure from
    out = list(heights)
    start = on.index(False)  # walk round the loop from a point off any bridge, so runs that wrap are whole
    runs, k = [], 0
    while k < n:
        i = (start + k) % n
        if on[i]:
            j = k
            while j + 1 < n and on[(start + j + 1) % n]:
                j += 1
            runs.append((k, j))
            k = j + 1
        else:
            k += 1
    for a, b in runs:
        lo, hi = a - 2, b + 2  # one point beyond each end for the abutment, and the height just past it
        h0, h1 = heights[(start + lo) % n], heights[(start + hi) % n]
        for k in range(lo + 1, hi):
            out[(start + k) % n] = h0 + (h1 - h0) * (k - lo) / (hi - lo)
    return out, len(runs)


def smooth(heights):
    """A 5-point median (25 m) to drop spikes, then two passes of a 7-point moving average (35 m), round the loop."""
    n = len(heights)
    med = [sorted(heights[(k + d) % n] for d in range(-2, 3))[2] for k in range(n)]
    for _ in range(2):
        med = [sum(med[(k + d) % n] for d in range(-3, 4)) / 7 for k in range(n)]
    return med


def climb(heights):
    """Total climbing round the loop, in metres."""
    n = len(heights)
    return sum(max(0.0, heights[(k + 1) % n] - heights[k]) for k in range(n))


def steepest(heights, step, over=20.0):
    """The steepest climb and descent, in percent, each measured over `over` metres."""
    n, k = len(heights), max(1, round(over / step))
    grades = [(heights[(i + k) % n] - heights[i]) / (k * step) * 100 for i in range(n)]
    return max(grades), min(grades)
