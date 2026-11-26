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
