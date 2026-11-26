import { test } from 'node:test';
import assert from 'node:assert/strict';
import { tileIndex } from '../../src/course/terrain-lod.js';

const TW = 101; // a 100-cell terrain
const xz = (k) => [k % TW, Math.floor(k / TW)];
const triangles = (idx) => Array.from({ length: idx.length / 3 }, (_, t) => [0, 1, 2].map((v) => xz(idx[t * 3 + v])));
const cross = ([p, q, r]) => (q[0] - p[0]) * (r[1] - p[1]) - (q[1] - p[1]) * (r[0] - p[0]);

test('step 1 is two triangles per cell, as the whole terrain is', () => {
  const idx = tileIndex(TW, 10, 20, 13, 22, 1);
  assert.equal(idx.length, 3 * 2 * 6);
  const a = 20 * TW + 10;
  assert.deepEqual([...idx.slice(0, 6)], [a, a + TW, a + 1, a + 1, a + TW, a + TW + 1]);
});

for (const [x0, z0, x1, z1] of [
  [0, 0, 40, 40],
  [17, 3, 78, 51], // sides that aren't a multiple of the step
  [60, 60, 100, 100],
])
  for (const s of [2, 4])
    test(`step ${s} on (${x0},${z0})-(${x1},${z1}): covers the tile once, wound the same way, edges whole`, () => {
      const tris = triangles(tileIndex(TW, x0, z0, x1, z1, s));
      const reference = Math.sign(cross(triangles(tileIndex(TW, x0, z0, x1, z1, 1))[0]));
      let area = 0;
      for (const t of tris) {
        const c = cross(t);
        assert.equal(Math.sign(c), reference, 'every triangle faces up');
        area += Math.abs(c) / 2;
        for (const [x, z] of t) assert.ok(x >= x0 && x <= x1 && z >= z0 && z <= z1, 'inside the tile');
      }
      assert.equal(area, (x1 - x0) * (z1 - z0), 'no gaps, no overlaps');
      // every edge segment of the tile, between neighbouring grid points, is a triangle side: no cracks
      const sides = new Set();
      for (const t of tris)
        for (let v = 0; v < 3; v++) {
          const [p, q] = [t[v], t[(v + 1) % 3]];
          sides.add([p, q].map(String).sort().join('|'));
        }
      const edge = [];
      for (let x = x0; x < x1; x++)
        edge.push(
          [
            [x, z0],
            [x + 1, z0],
          ],
          [
            [x, z1],
            [x + 1, z1],
          ],
        );
      for (let z = z0; z < z1; z++)
        edge.push(
          [
            [x0, z],
            [x0, z + 1],
          ],
          [
            [x1, z],
            [x1, z + 1],
          ],
        );
      for (const [p, q] of edge) assert.ok(sides.has([p, q].map(String).sort().join('|')), `edge ${p}-${q}`);
      assert.ok(tris.length < (x1 - x0) * (z1 - z0) * 2, 'fewer triangles than step 1');
    });

test('a tile too small for the step falls back to every point', () => {
  assert.deepEqual(tileIndex(TW, 0, 0, 6, 6, 4), tileIndex(TW, 0, 0, 6, 6, 1));
});
