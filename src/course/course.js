// The course: loads courses/<id>/ (see docs/refactor-plan.md, "Course format, version 1").
// ?course=<id> picks one from courses/index.json; anything not listed falls back to the valley.
import { $ } from '../util/dom.js';
import { OPTIONS } from '../options.js';
import { validateCourse, validateRoad, validateScenery, validateTerrain } from './validate.js';

// A broken course says why in place of the loading message, rather than leaving a blank page.
function fail(problems) {
  $('loading').textContent = 'This course could not be loaded: ' + problems.join('; ');
  throw new Error('ride: ' + problems.join('; '));
}
async function get(url, as) {
  let r;
  try {
    r = await fetch(url);
  } catch {
    fail([
      location.protocol === 'file:' ? 'run a local web server to ride (see the README)' : `could not fetch ${url}`,
    ]);
  }
  if (!r.ok) fail([`${url}: ${r.status} ${r.statusText}`]);
  try {
    return await r[as]();
  } catch {
    fail([`${url} is not valid ${as === 'json' ? 'JSON' : 'data'}`]);
  }
}
const check = (problems) => problems.length && fail(problems);

// Every course, for the menu and the ride log: [{ id, name, shortName, lengthKm, climbM }]
export const courses = await get('courses/index.json', 'json');
const id = courses.some((c) => c.id === OPTIONS.course) ? OPTIONS.course : 'valley';
export const dir = `courses/${id}/`; // the course's folder, for files loaded later (its photo)

export const course = await get(dir + 'course.json', 'json');
check(validateCourse(course, id));

// ?theme=christmas: the valley under snow at dusk, with lights in the trees and a few chalets
export const XMAS = OPTIONS.xmas && course.generator === 'valley';

// The surveyed ground, road and mapped scenery of a survey course; null for the invented valley.
export let real = null;
if (course.kind === 'survey') {
  $('loading').textContent = `Building ${course.name}…`;
  const t = course.terrain,
    file = course.scenery?.file;
  const [buf, road, scenery] = await Promise.all([
    get(dir + t.file, 'arrayBuffer'),
    get(dir + course.road, 'json'),
    file ? get(dir + file, 'json') : {},
  ]);
  check(validateTerrain(course, buf.byteLength));
  check(validateRoad(course, road));
  if (file) check(validateScenery(course, scenery));

  const g = t.cells,
    dv = new DataView(buf);
  // surveyed ground heights, metres: little-endian uint16 scaled between min and max
  const h = new Float32Array((g + 1) ** 2);
  for (let i = 0; i < h.length; i++) h[i] = t.min + (dv.getUint16(i * 2, true) / 65535) * (t.max - t.min);
  const wb = Uint8Array.from(atob(scenery.woods ?? ''), (c) => c.charCodeAt(0));
  real = {
    size: t.size,
    cells: g,
    h,
    road,
    buildings: scenery.buildings ?? [],
    trees: scenery.trees ?? [],
    lines: scenery.lines ?? [],
    // is this spot mapped as woodland?
    wood(x, z) {
      const ix = Math.round((x + t.size / 2) / (t.size / g)),
        iz = Math.round((z + t.size / 2) / (t.size / g));
      if (ix < 0 || iz < 0 || ix > g || iz > g) return false;
      const i = iz * (g + 1) + ix;
      return ((wb[i >> 3] >> (i & 7)) & 1) === 1;
    },
  };
}
$('credit').textContent = course.credits.map((c) => c.text).join(' ');

export function demH(x, z) {
  // the real ground under a point
  const g = real.cells,
    w = g + 1,
    f = (v) => Math.min(g - 1e-6, Math.max(0, (v + real.size / 2) / (real.size / g)));
  const fx = f(x),
    fz = f(z),
    ix = Math.floor(fx),
    iz = Math.floor(fz),
    u = fx - ix,
    v = fz - iz,
    h = real.h;
  return (
    (h[iz * w + ix] * (1 - u) + h[iz * w + ix + 1] * u) * (1 - v) +
    (h[(iz + 1) * w + ix] * (1 - u) + h[(iz + 1) * w + ix + 1] * u) * v
  );
}

export const st0 = {}; // build counts, for checking
