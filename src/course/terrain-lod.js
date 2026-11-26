// The triangles for one terrain tile at a level of detail. Pure: no Three.js, so it is unit-tested.
//
// The terrain is a grid of (tg + 1) × (tg + 1) points, row by row; a tile is the cells from (x0, z0) to (x1, z1).
// At step 1 every grid point is used, two triangles per cell. At step s > 1 the inside uses every s-th point, but the
// tile's edges keep every point, joined to the coarse inside by a strip of triangles, so a tile always meets its
// neighbours along the same line whatever their levels: no cracks.

// Triangles wind like step 1's (a, below a, right of a): clockwise seen from above, as Three.js expects here.
const winding = (p, q, r) => (q[0] - p[0]) * (r[1] - p[1]) - (q[1] - p[1]) * (r[0] - p[0]);

// coarse positions from a + s to b - s, every s, always ending at b - s
function inner(a, b, s) {
  const out = [];
  for (let v = a + s; v < b - s; v += s) out.push(v);
  out.push(b - s);
  return out;
}

export function tileIndex(tw, x0, z0, x1, z1, s = 1) {
  const out = [];
  const id = ([x, z]) => z * tw + x;
  const tri = (p, q, r) => {
    const w = winding(p, q, r);
    if (w === 0) return;
    if (w < 0) out.push(id(p), id(q), id(r));
    else out.push(id(p), id(r), id(q));
  };
  if (s === 1 || x1 - x0 <= 2 * s || z1 - z0 <= 2 * s) {
    for (let z = z0; z < z1; z++)
      for (let x = x0; x < x1; x++) {
        const a = z * tw + x,
          b = a + tw;
        out.push(a, b, a + 1, a + 1, b, b + 1);
      }
    return Uint32Array.from(out);
  }
  const gx = inner(x0, x1, s),
    gz = inner(z0, z1, s);
  for (let j = 0; j + 1 < gz.length; j++)
    for (let i = 0; i + 1 < gx.length; i++) {
      const a = [gx[i], gz[j]],
        b = [gx[i], gz[j + 1]],
        d = [gx[i + 1], gz[j]],
        c = [gx[i + 1], gz[j + 1]];
      tri(a, b, d);
      tri(d, b, c);
    }
  // a strip between an edge (every point) and the coarse line inside it, walked along `axis`
  const strip = (edge, line, axis) => {
    let i = 0,
      j = 0;
    while (i < edge.length - 1 || j < line.length - 1) {
      if (j === line.length - 1 || (i < edge.length - 1 && edge[i + 1][axis] <= line[j + 1][axis])) {
        tri(edge[i], edge[i + 1], line[j]);
        i++;
      } else {
        tri(edge[i], line[j + 1], line[j]);
        j++;
      }
    }
  };
  const range = (a, b) => Array.from({ length: b - a + 1 }, (_, k) => a + k);
  strip(
    range(x0, x1).map((x) => [x, z0]),
    gx.map((x) => [x, gz[0]]),
    0,
  ); // north
  strip(
    range(x0, x1).map((x) => [x, z1]),
    gx.map((x) => [x, gz.at(-1)]),
    0,
  ); // south
  strip(
    range(z0, z1).map((z) => [x0, z]),
    gz.map((z) => [gx[0], z]),
    1,
  ); // west
  strip(
    range(z0, z1).map((z) => [x1, z]),
    gz.map((z) => [gx.at(-1), z]),
    1,
  ); // east
  return Uint32Array.from(out);
}
