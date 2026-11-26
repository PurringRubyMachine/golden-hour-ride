// The validator cases shared with the Python validator (tests/course-cases.json).
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { validateCourse } from '../../src/course/validate.js';

const { bases, cases } = JSON.parse(readFileSync(new URL('../course-cases.json', import.meta.url), 'utf8'));

// walk a dotted path ("credits.0.licence") to the object holding its last key
function parent(obj, path) {
  const keys = path.split('.');
  const last = keys.pop();
  return [keys.reduce((o, k) => o[k], obj), last];
}

for (const c of cases) {
  test(c.name, () => {
    let course = structuredClone(bases[c.base]);
    for (const [path, value] of Object.entries(c.set ?? {})) {
      const [o, k] = parent(course, path);
      o[k] = value;
    }
    for (const path of c.delete ?? []) {
      const [o, k] = parent(course, path);
      delete o[k];
    }
    if ('replace' in c) course = c.replace;
    const problems = validateCourse(course, c.id ?? bases[c.base].id);
    if (c.problem === null) assert.deepEqual(problems, []);
    else
      assert.ok(
        problems.some((p) => p.includes(c.problem)),
        `expected "${c.problem}" in ${JSON.stringify(problems)}`,
      );
  });
}
