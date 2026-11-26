// Options read from the address bar.

// ?course=<id>         a course listed in courses/index.json (the loader falls back to the valley)
// ?theme=christmas     the valley under snow at dusk (valley only: see XMAS in course/course.js)
// ?scenery[=nobars]    drift along on its own with nothing on screen; nobars also hides the handlebars
// ?hills=<0-100>       how much of each hill a smart trainer feels, for this visit
// ?quality=<level>     auto, low, medium or high, for this visit (see render/quality.js)
// ?at, ?weather, ?freeze  test options: see tests/visual/README.md
export function parseOptions(search) {
  const q = new URLSearchParams(search);
  return {
    course: q.get('course') || 'valley',
    xmas: q.get('theme') === 'christmas',
    scenery: q.get('scenery'),
    hills: q.get('hills'),
    quality: ['auto', 'low', 'medium', 'high'].includes(q.get('quality')) ? q.get('quality') : null,
    at: parseFloat(q.get('at')),
    weather: q.has('weather') ? q.get('weather') : null,
    freeze: q.has('freeze'),
  };
}
// Outside a browser (in unit tests) there is no address bar, so every option takes its default.
export const OPTIONS = parseOptions(globalThis.location?.search ?? '');

// Scenery mode (?scenery): the ride drifts along on its own at a gentle pace with nothing on screen and the weather
// slowly changing, for leaving on in the background. ?scenery=nobars also hides the handlebars.
export const SCENERY = OPTIONS.scenery;

// Test options, for the screenshot tests: ?at=<metres> starts that far along the road; ?freeze stops the clock,
// so the rider, weather, wind and grain hold still and every frame is the same.
export const AT = OPTIONS.at,
  FREEZE = OPTIONS.freeze;
