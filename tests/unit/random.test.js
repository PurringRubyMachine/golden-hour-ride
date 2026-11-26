import { test } from 'node:test';
import assert from 'node:assert/strict';
import { makeRandom } from '../../src/util/random.js';

const take = (rnd, n) => Array.from({ length: n }, rnd);

test('the same name gives the same sequence', () => {
  assert.deepEqual(take(makeRandom('trees'), 50), take(makeRandom('trees'), 50));
});

test('different names give different sequences, even when the names are alike', () => {
  const a = take(makeRandom('grass patch 40'), 20);
  const b = take(makeRandom('grass patch 80'), 20);
  assert.notDeepEqual(a, b);
  // first values of similar names should not cluster (a plain LCG seeded 40 apart puts them within 0.02)
  const firsts = Array.from({ length: 50 }, (_, i) => makeRandom(`grass patch ${i * 40}`)());
  assert.ok(Math.max(...firsts) - Math.min(...firsts) > 0.5);
});

test('numbers are from 0 up to, not including, 1', () => {
  for (const x of take(makeRandom('range'), 10000)) assert.ok(x >= 0 && x < 1);
});
