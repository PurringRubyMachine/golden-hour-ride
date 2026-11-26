// The course map's geometry: fitting the loop and its height profile into the panel. Pure: no DOM, unit-tested.

// A transform that fits points [x, z] into a w × h box with `pad` round it, keeping their shape, centred, north up
// (z runs south, as screen y runs down). Returns ([x, z]) => [px, py].
export function fit(points, w, h, pad) {
  let x0 = Infinity,
    x1 = -Infinity,
    z0 = Infinity,
    z1 = -Infinity;
  for (const [x, z] of points) {
    x0 = Math.min(x0, x);
    x1 = Math.max(x1, x);
    z0 = Math.min(z0, z);
    z1 = Math.max(z1, z);
  }
  const scale = Math.min((w - 2 * pad) / (x1 - x0 || 1), (h - 2 * pad) / (z1 - z0 || 1)),
    ox = (w - (x1 - x0) * scale) / 2,
    oz = (h - (z1 - z0) * scale) / 2;
  return ([x, z]) => [ox + (x - x0) * scale, oz + (z - z0) * scale];
}

// Every `step`-th item, always ending with the last, so a long road draws quickly without losing its ends.
export function thin(items, step) {
  const out = items.filter((_, i) => i % step === 0);
  if ((items.length - 1) % step !== 0) out.push(items.at(-1));
  return out;
}

// The height profile as points in a w × h box: x along the loop (0 to length), y up for higher ground. heights[i] is
// at distance dist[i]. Returns { points, lo, hi } with the lowest and highest heights.
export function profile(dist, heights, length, w, h, pad) {
  const lo = Math.min(...heights),
    hi = Math.max(...heights),
    span = Math.max(hi - lo, 20); // a flat course still shows its small rises as small
  const points = dist.map((d, i) => [(d / length) * w, h - pad - ((heights[i] - lo) / span) * (h - 2 * pad)]);
  return { points, lo, hi };
}

// "17.4 of 41.0 km": where the rider is on the loop, from the course's beginning, whatever the start.
export function whereOnLoop(s, length) {
  const at = (((s % length) + length) % length) / 1000;
  return `${at.toFixed(1)} of ${(length / 1000).toFixed(1)} km`;
}
