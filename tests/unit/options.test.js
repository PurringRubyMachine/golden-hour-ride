import { test } from 'node:test';
import assert from 'node:assert/strict';
import { parseOptions } from '../../src/options.js';

test('defaults: the valley, no theme, no test options', () => {
  const o = parseOptions('');
  assert.equal(o.course, 'valley');
  assert.equal(o.xmas, false);
  assert.equal(o.scenery, null);
  assert.equal(o.hills, null);
  assert.ok(Number.isNaN(o.at));
  assert.equal(o.weather, null);
  assert.equal(o.freeze, false);
});

test('course: the id is passed on as written, for the loader to look up', () => {
  assert.equal(parseOptions('?course=leckhampton').course, 'leckhampton');
  assert.equal(parseOptions('?course=').course, 'valley');
});

test('the Christmas theme is asked for here; the loader decides whether the course has it', () => {
  assert.equal(parseOptions('?theme=christmas').xmas, true);
  assert.equal(parseOptions('?theme=easter').xmas, false);
});

test('scenery mode, with or without the handlebars', () => {
  assert.equal(parseOptions('?scenery').scenery, '');
  assert.equal(parseOptions('?scenery=nobars').scenery, 'nobars');
});

test('test options', () => {
  const o = parseOptions('?at=120.5&weather=mist&freeze');
  assert.equal(o.at, 120.5);
  assert.equal(o.weather, 'mist');
  assert.equal(o.freeze, true);
  assert.equal(parseOptions('?weather').weather, '');
});

test('the hills value is passed on as written, for the trainer code to check', () => {
  assert.equal(parseOptions('?hills=70').hills, '70');
});
