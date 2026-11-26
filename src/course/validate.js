// Checks a course against format 1 (docs/refactor-plan.md, "Course format, version 1").
// Each function returns a list of problems, empty when all is well. No DOM and no Three.js, so the unit tests
// can run it over every course in courses/.

export const FORMAT = 1;
export const GENERATORS = ['valley'];
export const SCENERY_STYLES = ['pastoral-1800s', 'plain'];

const isNum = (v) => typeof v === 'number' && Number.isFinite(v);
const isText = (v) => typeof v === 'string' && v.trim() !== '';
const isObj = (v) => typeof v === 'object' && v !== null && !Array.isArray(v);
const isPoint = (p, n) => Array.isArray(p) && p.length === n && p.every(isNum);
// strict base64: groups of four characters, padded with = only at the end, so atob() in the loader can't fail
const isBase64 = (s) => /^(?:[A-Za-z0-9+/]{4})*(?:[A-Za-z0-9+/]{2}==|[A-Za-z0-9+/]{3}=)?$/.test(s);

// course.json. id is the folder name, which the course's own id must match.
export function validateCourse(c, id) {
  if (!isObj(c)) return ['course.json must be an object'];
  const bad = [];
  const need = (ok, problem) => ok || bad.push(problem);

  need(c.format === FORMAT, `format must be ${FORMAT}`);
  need(c.id === id, `id must be "${id}", the name of the course's folder`);
  need(typeof id === 'string' && /^[a-z0-9][a-z0-9-]*$/.test(id), 'id must be lower-case letters, digits and hyphens');
  need(isText(c.name), 'name is required');
  need(c.shortName === undefined || isText(c.shortName), 'shortName must be text');
  need(c.description === undefined || typeof c.description === 'string', 'description must be text');
  need(c.loop === true, 'loop must be true: format 1 supports loops only');
  need(c.start === undefined || (isNum(c.start) && c.start >= 0), 'start must be a distance in metres, 0 or more');

  need(Array.isArray(c.credits), 'credits must be a list');
  if (Array.isArray(c.credits))
    c.credits.forEach((cr, i) => {
      need(isObj(cr) && isText(cr.text), `credits[${i}].text is required`);
      need(isObj(cr) && isText(cr.licence), `credits[${i}].licence is required`);
      need(!isObj(cr) || cr.url === undefined || isText(cr.url), `credits[${i}].url must be text`);
    });

  if (c.kind === 'procedural') {
    need(GENERATORS.includes(c.generator), `generator must be one of: ${GENERATORS.join(', ')}`);
  } else if (c.kind === 'survey') {
    need(
      !Array.isArray(c.credits) || c.credits.length > 0, // (a missing list is reported above)
      'credits must name the sources of the data and their licences',
    );
    const o = c.origin;
    need(isObj(o) && isText(o.crs) && isNum(o.x) && isNum(o.y), 'origin needs crs, x and y');
    const t = c.terrain;
    if (!isObj(t)) bad.push('terrain is required');
    else {
      need(isText(t.file), 'terrain.file is required');
      need(isNum(t.size) && t.size > 0, 'terrain.size must be a width in metres');
      need(Number.isInteger(t.cells) && t.cells > 0, 'terrain.cells must be a whole number');
      need(isNum(t.min) && isNum(t.max) && t.min < t.max, 'terrain.min and terrain.max must be heights, min below max');
    }
    need(isText(c.road), 'road must name the road file');
    const s = c.scenery;
    if (s !== undefined) {
      if (!isObj(s)) bad.push('scenery must be an object');
      else {
        need(s.file === undefined || isText(s.file), 'scenery.file must be text');
        need(SCENERY_STYLES.includes(s.style), `scenery.style must be one of: ${SCENERY_STYLES.join(', ')}`);
        const op = s.options ?? {};
        need(isObj(op), 'scenery.options must be an object');
        need(op.sheepAbove === undefined || isNum(op.sheepAbove), 'scenery.options.sheepAbove must be a height');
        need(op.stooksBelow === undefined || isNum(op.stooksBelow), 'scenery.options.stooksBelow must be a height');
        need(
          op.smoke === undefined || (Array.isArray(op.smoke) && op.smoke.every((p) => isPoint(p, 2))),
          'scenery.options.smoke must be a list of [x, z] points',
        );
      }
    }
  } else bad.push('kind must be "survey" or "procedural"');
  return bad;
}

// terrain.bin: (cells + 1)² little-endian uint16 heights.
export function validateTerrain(c, byteLength) {
  const want = (c.terrain.cells + 1) ** 2 * 2;
  return byteLength === want ? [] : [`${c.terrain.file} is ${byteLength} bytes; ${want} expected`];
}

// road.json: [[x, y, z], ...] in metres, inside the terrain.
export function validateRoad(c, road) {
  if (!Array.isArray(road) || road.length < 4) return [`${c.road} must list at least 4 points`];
  const half = c.terrain.size / 2;
  const i = road.findIndex((p) => !isPoint(p, 3));
  if (i >= 0) return [`${c.road}: point ${i} must be [x, y, z] in metres`];
  const out = road.findIndex(([x, , z]) => Math.abs(x) > half || Math.abs(z) > half);
  return out >= 0 ? [`${c.road}: point ${out} is outside the terrain`] : [];
}

// scenery.json: buildings, trees, lines and the woodland mask, all optional.
export function validateScenery(c, sc) {
  if (!isObj(sc)) return [`${c.scenery.file} must be an object`];
  const bad = [];
  for (const [key, n] of [
    ['buildings', 7],
    ['trees', 2],
    ['lines', 5],
  ])
    if (sc[key] !== undefined && !(Array.isArray(sc[key]) && sc[key].every((p) => isPoint(p, n))))
      bad.push(`${c.scenery.file}: ${key} must be a list of ${n}-number entries`);
  if (sc.woods !== undefined) {
    const bytes = Math.ceil((c.terrain.cells + 1) ** 2 / 8),
      chars = 4 * Math.ceil(bytes / 3);
    if (typeof sc.woods !== 'string' || (sc.woods !== '' && (sc.woods.length !== chars || !isBase64(sc.woods))))
      bad.push(`${c.scenery.file}: woods must be ${chars} characters of base64 (one bit per terrain point)`);
  }
  return bad;
}
