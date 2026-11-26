// The quality level: the rider's choice (Auto, Low, Medium or High), applied while riding. The levels and the
// automatic choice are in quality-levels.js. Modules that depend on the level register with onQuality.
import { FREEZE, OPTIONS } from '../options.js';
import { uPx } from '../uniforms.js';
import { renderer } from './renderer.js';
import { LEVELS, SETTINGS, autoQuality, startLevel } from './quality-levels.js';

const MODES = ['auto', ...LEVELS];
const KEY = 'golden-hour-ride-quality'; // kept in this browser: { mode, auto }, the rider's choice and Auto's level
const stored = (() => {
  try {
    return JSON.parse(localStorage.getItem(KEY)) || {};
  } catch {
    return {};
  }
})();
const save = () => {
  try {
    localStorage.setItem(KEY, JSON.stringify({ mode: stored.mode, auto: quality.auto.level }));
  } catch {}
};

const gpu = (() => {
  const gl = renderer.getContext(),
    info = gl.getExtension('WEBGL_debug_renderer_info');
  return info ? gl.getParameter(info.UNMASKED_RENDERER_WEBGL) : '';
})();
// Auto starts where it settled last time in this browser, but never above where this graphics chip would start.
const guess = startLevel(gpu),
  start = LEVELS.includes(stored.auto) && LEVELS.indexOf(stored.auto) < LEVELS.indexOf(guess) ? stored.auto : guess;

export const quality = {
  // ?quality= for this visit; the screenshot tests (?freeze) use High, so they don't depend on the machine
  mode: OPTIONS.quality ?? (FREEZE ? 'high' : MODES.includes(stored.mode) ? stored.mode : 'auto'),
  gpu,
  auto: autoQuality(start),
  get level() {
    return this.mode === 'auto' ? this.auto.level : this.mode;
  },
};

const fns = [];
let applied = quality.level;
// fn(settings, level) now, and again whenever the level changes
export function onQuality(fn) {
  fns.push(fn);
  fn(SETTINGS[applied], applied);
}
function apply() {
  if (quality.level === applied) return;
  applied = quality.level;
  for (const fn of fns) fn(SETTINGS[applied], applied);
}

// the rider's choice, kept for next time
export function setQualityMode(mode) {
  quality.mode = stored.mode = mode;
  save();
  apply();
}

// every frame, from the ride loop: lets Auto step down if the frames are slow
export function qualityFrame(ms, now) {
  if (quality.mode !== 'auto' || FREEZE) return;
  if (quality.auto.frame(ms, now)) {
    save();
    apply();
  }
}

// Fewer pixels: the picture is drawn smaller and stretched to the window. Point sizes (snow, lights, smoke) are in
// drawn pixels, so they follow.
onQuality((s) => {
  renderer.setPixelRatio(s.scale);
  uPx.value = (innerHeight * s.scale) / (2 * Math.tan(0.6));
});
