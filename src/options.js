// Options read from the address bar.

// ?course=leckhampton  the real Leckhampton loop instead of the invented valley
// ?theme=christmas     the valley under snow at dusk (valley only)
// ?scenery[=nobars]    drift along on its own with nothing on screen; nobars also hides the handlebars
// ?hills=<0-100>       how much of each hill a smart trainer feels, for this visit
// ?at, ?weather, ?freeze  test options: see tests/visual/README.md
function parseOptions(search) {
  const q = new URLSearchParams(search);
  return {
    course: q.get('course') === 'leckhampton' ? 'leckhampton' : 'valley',
    xmas: q.get('theme') === 'christmas' && q.get('course') !== 'leckhampton',
    scenery: q.get('scenery'),
    hills: q.get('hills'),
    at: parseFloat(q.get('at')),
    weather: q.has('weather') ? q.get('weather') : null,
    freeze: q.has('freeze'),
  };
}
export const OPTIONS = parseOptions(location.search);

// ?theme=christmas: the same valley under snow at dusk, with lights in the trees and a few chalets
export const XMAS = OPTIONS.xmas;

export const COURSE = OPTIONS.course;
// Scenery mode (?scenery): the ride drifts along on its own at a gentle pace with nothing on screen and the weather
// slowly changing, for leaving on in the background. ?scenery=nobars also hides the handlebars.
export const SCENERY = OPTIONS.scenery;

// Test options, for the screenshot tests: ?at=<metres> starts that far along the road; ?freeze stops the clock,
// so the rider, weather, wind and grain hold still and every frame is the same.
export const AT = OPTIONS.at,
  FREEZE = OPTIONS.freeze;
