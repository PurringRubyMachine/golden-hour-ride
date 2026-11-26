// The Quality button: each click moves on through Auto, Low, Medium and High. Auto starts from the graphics chip and
// steps down if the ride isn't smooth; the label shows the level it is on.
import { $ } from '../util/dom.js';
import { onQuality, quality, setQualityMode } from '../render/quality.js';

const MODES = ['auto', 'low', 'medium', 'high'],
  NAMES = { auto: 'Auto', low: 'Low', medium: 'Medium', high: 'High' };
const btn = $('quality');
const label = () => {
  btn.textContent = 'Quality: ' + (quality.mode === 'auto' ? `Auto (${NAMES[quality.level]})` : NAMES[quality.mode]);
};
btn.addEventListener('click', () => {
  setQualityMode(MODES[(MODES.indexOf(quality.mode) + 1) % MODES.length]);
  label();
});
onQuality(label); // and again whenever Auto steps down
