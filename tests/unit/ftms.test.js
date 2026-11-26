import { test } from 'node:test';
import assert from 'node:assert/strict';
import { simParams, trainerGrade, OP_SIM } from '../../src/devices/ftms.js';

const bytes = (view) => [...new Uint8Array(view.buffer)];

test('Indoor Bike Simulation Parameters: op code, no wind, gradient, rolling resistance and drag', () => {
  // gradient 5 % = 500 in 0.01 % units, little-endian; Crr 0.004 = 40 in 0.0001 units; drag 0.192 kg/m = 19 in 0.01 units
  assert.deepEqual(bytes(simParams(5)), [OP_SIM, 0x00, 0x00, 0xf4, 0x01, 40, 19]);
});

test('a descent is sent as a negative gradient', () => {
  assert.deepEqual(bytes(simParams(-3.5)).slice(3, 5), [0xa2, 0xfe]); // -350 as a little-endian int16
});

test('gradient is rounded to the nearest 0.01 %', () => {
  assert.equal(simParams(2.346).getInt16(3, true), 235);
});

test('the trainer feels the hills setting on climbs, and half of it on descents', () => {
  assert.equal(trainerGrade(10, 0.5), 5);
  assert.equal(trainerGrade(-10, 0.5), -2.5);
  assert.equal(trainerGrade(8, 1), 8);
  assert.equal(trainerGrade(8, 0), 0);
});

test('gradients beyond 20 % are capped before scaling', () => {
  assert.equal(trainerGrade(30, 1), 20);
  assert.equal(trainerGrade(-30, 1), -10);
});
