import { test } from 'node:test';
import assert from 'node:assert/strict';
import { validateCourse, validateRoad, validateScenery, validateTerrain } from '../../src/course/validate.js';

const survey = () => ({
  format: 1,
  id: 'my-loop',
  name: 'My Loop',
  kind: 'survey',
  loop: true,
  start: 0,
  origin: { crs: 'EPSG:2958', x: 500000, y: 4800000 },
  terrain: { file: 'terrain.bin', size: 1000, cells: 100, min: 10, max: 90 },
  road: 'road.json',
  scenery: { file: 'scenery.json', style: 'plain', options: {} },
  credits: [{ text: 'Heights: HRDEM', licence: 'OGL-Canada-2.0' }],
});
const procedural = {
  format: 1,
  id: 'valley',
  name: 'Valley',
  kind: 'procedural',
  generator: 'valley',
  loop: true,
  credits: [],
};
// the one problem a change causes, matched on a word from its message
const problem = (change, id = 'my-loop') => {
  const c = survey();
  change(c);
  return validateCourse(c, id);
};

test('valid courses pass', () => {
  assert.deepEqual(validateCourse(survey(), 'my-loop'), []);
  assert.deepEqual(validateCourse(procedural, 'valley'), []);
});

test('each broken field is reported', () => {
  assert.match(problem((c) => (c.format = 2)).join(), /format/);
  assert.match(problem(() => {}, 'other').join(), /folder/);
  assert.match(problem((c) => (c.loop = false)).join(), /loops only/);
  assert.match(problem((c) => (c.kind = 'imaginary')).join(), /kind/);
  assert.match(problem((c) => (c.terrain.max = 5)).join(), /min below max/);
  assert.match(problem((c) => delete c.road).join(), /road/);
  assert.match(problem((c) => (c.scenery.style = 'gothic')).join(), /scenery.style/);
  assert.match(problem((c) => (c.scenery.options.smoke = [[1, 2, 3]])).join(), /smoke/);
  assert.match(problem((c) => (c.start = -5)).join(), /start/);
});

test('a survey course must credit its data, with a licence for each source', () => {
  assert.match(problem((c) => (c.credits = [])).join(), /credits must name/);
  assert.match(problem((c) => delete c.credits[0].licence).join(), /licence/);
});

test('an upper-case or spaced id is refused', () => {
  const c = { ...procedural, id: 'My Loop' };
  assert.match(validateCourse(c, 'My Loop').join(), /lower-case/);
});

test('terrain must hold (cells + 1)² heights of two bytes', () => {
  assert.deepEqual(validateTerrain(survey(), 101 * 101 * 2), []);
  assert.equal(validateTerrain(survey(), 100 * 100 * 2).length, 1);
});

test('road points must be [x, y, z] inside the terrain', () => {
  const sq = [
    [0, 1, 0],
    [100, 1, 0],
    [100, 1, 100],
    [0, 1, 100],
  ];
  assert.deepEqual(validateRoad(survey(), sq), []);
  assert.match(validateRoad(survey(), sq.slice(0, 3)).join(), /at least 4/);
  assert.match(validateRoad(survey(), [...sq, [0, 1]]).join(), /point 4/);
  assert.match(validateRoad(survey(), [...sq, [600, 1, 0]]).join(), /outside/);
});

test('scenery entries and the woodland mask are checked', () => {
  assert.deepEqual(validateScenery(survey(), {}), []);
  assert.deepEqual(
    validateScenery(survey(), { trees: [[1, 2]], woods: 'A'.repeat(4 * Math.ceil(Math.ceil(101 ** 2 / 8) / 3)) }),
    [],
  );
  assert.match(validateScenery(survey(), { trees: [[1, 2, 3]] }).join(), /trees/);
  assert.match(validateScenery(survey(), { woods: 'AAAA' }).join(), /woods/);
});
