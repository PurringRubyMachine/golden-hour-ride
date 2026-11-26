import { test } from 'node:test';
import assert from 'node:assert/strict';
import { fit, profile, thin, whereOnLoop } from '../../src/ui/map-geometry.js';

test('fit keeps the shape, centres it, and stays inside the padding', () => {
  const pts = [
    [-1000, -200],
    [3000, -200],
    [3000, 600],
    [-1000, 600],
  ]; // 4 km east-west, 800 m north-south
  const f = fit(pts, 200, 140, 10);
  const out = pts.map(f);
  for (const [x, y] of out) assert.ok(x >= 10 - 1e-9 && x <= 190 + 1e-9 && y >= 10 - 1e-9 && y <= 130 + 1e-9);
  const w = out[1][0] - out[0][0],
    h = out[2][1] - out[1][1];
  assert.ok(Math.abs(w / h - 5) < 1e-9, 'same shape: 5 to 1');
  assert.equal(w, 180, 'the long side fills the width');
  assert.ok(Math.abs((out[0][1] + out[2][1]) / 2 - 70) < 1e-9, 'centred vertically');
  assert.ok(f([0, -200])[1] < f([0, 600])[1], 'north (smaller z) is up');
});

test('thin keeps every nth point and always the last', () => {
  assert.deepEqual(thin([0, 1, 2, 3, 4, 5, 6], 3), [0, 3, 6]);
  assert.deepEqual(thin([0, 1, 2, 3, 4, 5, 6, 7], 3), [0, 3, 6, 7]);
});

test('profile: x along the loop, higher ground higher up', () => {
  const { points, lo, hi } = profile([0, 500, 1000], [100, 160, 100], 1000, 200, 40, 4);
  assert.equal(lo, 100);
  assert.equal(hi, 160);
  assert.deepEqual(
    points.map((p) => p[0]),
    [0, 100, 200],
  );
  assert.equal(points[0][1], 36);
  assert.equal(points[1][1], 4);
});

test('a flat course shows its small rises as small', () => {
  const { points } = profile([0, 1], [50, 52], 1, 100, 44, 4);
  assert.ok(points[0][1] - points[1][1] < 10);
});

test('where on the loop, from the beginning, whatever the start', () => {
  assert.equal(whereOnLoop(17410, 41020), '17.4 of 41.0 km');
  assert.equal(whereOnLoop(41020 + 500, 41020), '0.5 of 41.0 km');
  assert.equal(whereOnLoop(-250, 3300), '3.0 of 3.3 km');
});
