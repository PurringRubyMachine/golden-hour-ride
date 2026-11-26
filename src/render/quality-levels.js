// Quality levels, and the automatic choice between them. Pure: no DOM, no Three.js, so it is unit-tested.
// See docs/performance-plan.md for the measurements behind these numbers.

export const LEVELS = ['low', 'medium', 'high'];

// scale: pixels drawn per screen (CSS) pixel. It matters most on built-in graphics, which are limited by how many
// pixels they shade. shadows: shadow map size, 0 for none (the sun is low, so the shadowed area reaches 700 m back
// towards it and takes in a lot of woodland: shadows cost a built-in chip a quarter of its frames even at 1024). msaa: anti-aliasing samples. meadow: grass tufts in the
// field round the rider. verge: how far ahead and behind the verge grass is drawn, in metres. trunks: how far away
// tree trunks are drawn, in metres; beyond that they are hidden under the crowns and a pixel or two wide. trees: the
// same for whole trees; beyond it the woods carry on as the ground's canopy colour. treeDensity, vergeDensity: the
// share of the trees, and of the verge grass, that is drawn.
// terrainNear, terrainMid: the ground is drawn in full out to terrainNear metres, at half detail out to terrainMid, and
// at a quarter beyond. photoFrom, photoTo: on a course with a photo of the ground from above, the photo takes over the
// ground's colour from photoFrom metres away and has it all by photoTo; photoSize: how many pixels across of it are
// loaded (a 4096-pixel photo takes about 90 MB of graphics memory, a 2048 one a quarter of that).
export const SETTINGS = {
  low: {
    scale: 0.5,
    shadows: 0,
    bloom: false,
    rays: false,
    msaa: 0,
    meadow: 30000,
    verge: 140,
    vergeDensity: 0.5,
    trees: 1000,
    treeDensity: 0.6,
    trunks: 250,
    terrainNear: 800,
    terrainMid: 2000,
    photoFrom: 60,
    photoTo: 200,
    photoSize: 2048,
  },
  medium: {
    scale: 0.7,
    shadows: 2048,
    bloom: true,
    rays: true,
    msaa: 2,
    meadow: 130000,
    verge: 200,
    vergeDensity: 0.8,
    trees: 2000,
    treeDensity: 1,
    trunks: 400,
    terrainNear: 1200,
    terrainMid: 3000,
    photoFrom: 80,
    photoTo: 250,
    photoSize: 4096,
  },
  high: {
    scale: 1,
    shadows: 4096,
    bloom: true,
    rays: true,
    msaa: 4,
    meadow: 260000,
    verge: 230,
    vergeDensity: 1,
    trees: Infinity,
    treeDensity: 1,
    trunks: Infinity,
    terrainNear: 1500,
    terrainMid: 3500,
    photoFrom: 80,
    photoTo: 250,
    photoSize: 4096,
  },
};

// Where the automatic choice starts, from the graphics chip's name (WEBGL_debug_renderer_info): built-in graphics
// start at Medium, software rendering at Low, anything else at High. Discrete cards' names can include "Mesa" (AMD on
// Linux) or "Intel" (Arc), so those words alone don't decide it.
export function startLevel(gpu = '') {
  if (/SwiftShader|llvmpipe|softpipe|Software/i.test(gpu)) return 'low';
  if (/Intel/i.test(gpu) && !/\bArc\b/i.test(gpu)) return 'medium';
  if (/Radeon(\(TM\))? (Graphics|Vega)|Apple|Mali|Adreno|PowerVR/i.test(gpu)) return 'medium';
  return 'high';
}

// The automatic choice. Feed it every frame's length; it steps down a level when more than a quarter of the last
// 3 seconds went on slow frames (over 20 ms), ignoring the first 5 seconds (loading) and waiting 5 seconds after each
// step for the new level to settle. It counts time, not frames: a struggling chip often draws most frames on time and
// then stalls for most of a second, so slow frames are few but take most of the time. It never steps up: on a 60 Hz screen every frame takes 16.7 ms however fast the chip is,
// so there is no telling how much room there is. A rider can always choose a higher level by hand.
export function autoQuality(start, { settle = 5000, span = 3000, slow = 20, share = 0.25, rest = 5000 } = {}) {
  let level = start,
    from = null,
    frames = [];
  return {
    get level() {
      return level;
    },
    // ms: time since the previous frame; now: the time, in ms. Returns the new level when it steps down, else null.
    frame(ms, now) {
      if (from === null) from = now + settle;
      if (now < from || level === LEVELS[0]) return null;
      frames.push([now, ms]);
      while (frames[0][0] < now - span) frames.shift();
      if (now - from < span) return null; // not a full span yet
      let all = 0,
        late = 0;
      for (const [, m] of frames) {
        all += m;
        if (m > slow) late += m;
      }
      if (late <= all * share) return null;
      level = LEVELS[LEVELS.indexOf(level) - 1];
      from = now + rest;
      frames = [];
      return level;
    },
  };
}
