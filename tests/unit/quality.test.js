import { test } from 'node:test';
import assert from 'node:assert/strict';
import { LEVELS, SETTINGS, autoQuality, startLevel } from '../../src/render/quality-levels.js';

test('every level has every setting, and each is no more than the level above', () => {
  const keys = Object.keys(SETTINGS.high);
  for (const level of LEVELS) assert.deepEqual(Object.keys(SETTINGS[level]), keys);
  for (let i = 1; i < LEVELS.length; i++)
    for (const k of keys) assert.ok(+SETTINGS[LEVELS[i - 1]][k] <= +SETTINGS[LEVELS[i]][k], `${k} at ${LEVELS[i]}`);
});

test('the start: built-in graphics at Medium, software at Low, the rest at High', () => {
  const cases = [
    ['ANGLE (Intel, Mesa Intel(R) UHD Graphics (CML GT2), OpenGL ES 3.2)', 'medium'],
    ['ANGLE (Intel, Intel(R) Iris(R) Xe Graphics Direct3D11 vs_5_0 ps_5_0, D3D11)', 'medium'],
    ['ANGLE (AMD, AMD Radeon(TM) Graphics Direct3D11 vs_5_0 ps_5_0, D3D11)', 'medium'],
    ['ANGLE (Apple, ANGLE Metal Renderer: Apple M1, Unspecified Version)', 'medium'],
    ['ANGLE (Google, Vulkan 1.3.0 (SwiftShader Device (Subzero)), SwiftShader driver)', 'low'],
    ['ANGLE (NVIDIA Corporation, NVIDIA GeForce RTX 2060 with Max-Q Design/PCIe/SSE2, OpenGL 4.5.0)', 'high'],
    ['ANGLE (AMD, AMD Radeon RX 6600 (radeonsi, navi23, LLVM 15.0.7), OpenGL 4.6 Mesa 23.2.1)', 'high'],
    ['ANGLE (Intel, Intel(R) Arc(TM) A770 Graphics Direct3D11 vs_5_0 ps_5_0, D3D11)', 'high'],
    ['', 'high'],
  ];
  for (const [gpu, level] of cases) assert.equal(startLevel(gpu), level, gpu);
});

// frames of a given length for a given time, from t, through q; returns the levels it stepped to and the end time
const run = (q, t, ms, seconds) => {
  const steps = [];
  for (const end = t + seconds * 1000; t < end; t += ms) {
    const s = q.frame(ms, t);
    if (s) steps.push(s);
  }
  return { steps, t };
};

test('a smooth ride stays where it started', () => {
  assert.deepEqual(run(autoQuality('high'), 0, 16.7, 60).steps, []);
});

test('slow frames step down one level at a time, resting between steps, and stop at Low', () => {
  const q = autoQuality('high');
  assert.deepEqual(run(q, 0, 16.7, 1).steps, []);
  const { steps, t } = run(q, 1000, 100, 30);
  assert.deepEqual(steps, ['medium', 'low']);
  assert.equal(q.level, 'low');
  assert.deepEqual(run(q, t, 100, 30).steps, []);
});

test('nothing during the first 5 seconds counts: loading is slow', () => {
  const q = autoQuality('high');
  assert.deepEqual(run(q, 0, 200, 4.9).steps, []);
  assert.deepEqual(run(q, 4900, 16.7, 10).steps, []);
});

test('a few slow frames, under a quarter of the time, are not enough', () => {
  const q = autoQuality('medium');
  let t = 0;
  for (let i = 0; i < 2000; i++, t += 16.7) assert.equal(q.frame(i % 12 === 0 ? 40 : 16.7, t), null);
});

test('most frames on time but long stalls between them: steps down', () => {
  // as measured on Intel UHD 630 at Medium: 16.7 ms frames with stalls of a quarter of a second between them
  const q = autoQuality('medium');
  let t = 0,
    step = null;
  for (let i = 0; i < 400 && !step; i++) {
    const ms = i % 12 === 11 ? 265 : 16.7; // 1 frame in 12: too few to notice by counting
    t += ms;
    step = q.frame(ms, t);
  }
  assert.equal(step, 'low');
});

test('the frames after a step are judged afresh', () => {
  const q = autoQuality('high');
  run(q, 0, 16.7, 6);
  const slow = run(q, 6000, 50, 3.5);
  assert.deepEqual(slow.steps, ['medium']);
  assert.deepEqual(run(q, slow.t, 16.7, 30).steps, []);
});
