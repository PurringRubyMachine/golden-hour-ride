// Every course in courses/ must load: listed in the index, and valid against the course format.
// Data checks only, so this stays fast however many courses there are.
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync, readdirSync, statSync, existsSync } from 'node:fs';
import { validateCourse, validateRoad, validateScenery, validateTerrain } from '../../src/course/validate.js';

const root = new URL('../../courses/', import.meta.url);
const json = (path) => JSON.parse(readFileSync(new URL(path, root), 'utf8'));
const index = json('index.json');
const folders = readdirSync(root).filter((f) => statSync(new URL(f, root)).isDirectory());

test('the index lists every course folder, once, and nothing else', () => {
  const ids = index.map((e) => e.id);
  assert.deepEqual([...ids].sort(), [...folders].sort());
  assert.equal(new Set(ids).size, ids.length);
  assert.equal(ids[0], 'valley', 'the valley comes first: it is the default course');
});

for (const id of folders) {
  test(`course: ${id}`, () => {
    const c = json(`${id}/course.json`);
    assert.deepEqual(validateCourse(c, id), []);
    const entry = index.find((e) => e.id === id);
    assert.equal(entry.name, c.name, 'index.json name matches course.json');
    assert.equal(entry.shortName, c.shortName, 'index.json shortName matches course.json');
    assert.ok(entry.lengthKm > 0 && entry.climbM >= 0, 'index.json has the length and climbing');
    if (c.kind !== 'survey') return;
    assert.deepEqual(validateTerrain(c, statSync(new URL(`${id}/${c.terrain.file}`, root)).size), []);
    assert.deepEqual(validateRoad(c, json(`${id}/${c.road}`)), []);
    if (c.scenery?.file) {
      assert.ok(existsSync(new URL(`${id}/${c.scenery.file}`, root)), `${c.scenery.file} exists`);
      assert.deepEqual(validateScenery(c, json(`${id}/${c.scenery.file}`)), []);
    }
  });
}
