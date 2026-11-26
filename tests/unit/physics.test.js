import { test } from 'node:test';
import assert from 'node:assert/strict';
import { nextSpeed, MASS, CRR, DRAG } from '../../src/physics.js';

// Ride for a simulated minute or so and return the speed it settles at.
const settle = (power, climb, v = 5) => {
  for (let i = 0; i < 20000; i++) v = nextSpeed(v, power, climb, 0.05);
  return v;
};

test('no time passing leaves the speed alone', () => {
  assert.equal(nextSpeed(8, 300, 0.05, 0), 8);
});

test('on the flat, power balances rolling resistance and air drag', () => {
  const v = settle(220, 0);
  assert.ok(v > 9.8 && v < 10.1, `220 W on the flat settles near 36 km/h, got ${(v * 3.6).toFixed(1)}`);
  const needed = v * (MASS * 9.81 * CRR + DRAG * v * v);
  assert.ok(Math.abs(needed - 220) < 0.5, `power to hold that speed is ${needed.toFixed(1)} W`);
});

test('more power is faster, and climbing is slower', () => {
  assert.ok(settle(300, 0) > settle(200, 0));
  assert.ok(settle(220, 0.05) < settle(220, 0));
});

test('descents count half: a 6 % descent helps as much as a 3 % climb hinders', () => {
  const flat = nextSpeed(8, 200, 0, 0.05);
  const helped = nextSpeed(8, 200, -0.06, 0.05) - flat;
  const hindered = flat - nextSpeed(8, 200, 0.03, 0.05);
  assert.ok(Math.abs(helped - hindered) < 1e-12, `${helped} vs ${hindered}`);
});

test('the rider brakes above 54 km/h, so a steep descent does not run away', () => {
  const v = settle(0, -0.2);
  assert.ok(v > 15 && v < 16.5, `freewheeling down 20 % settles at ${(v * 3.6).toFixed(1)} km/h`);
});

test('speed never drops below 0.5 m/s', () => {
  assert.equal(nextSpeed(0.55, 0, 0.2, 0.05), 0.5);
  assert.equal(settle(0, 0.2), 0.5);
});
