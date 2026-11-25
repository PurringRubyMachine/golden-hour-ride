// Keys, the power slider, skipping, and hiding the display.
import { $ } from '../util/dom.js';
import { LEN } from '../course/road.js';
import { st } from '../state.js';

export const skip = (m) => {
  st.s = (((st.s + m) % LEN) + LEN) % LEN;
};
export const setTarget = (w) => {
  st.target = Math.min(900, Math.max(0, w));
  $('pwr').value = st.target;
};
addEventListener('keydown', (e) => {
  if (e.key === 'ArrowUp') setTarget(st.target + 10);
  if (e.key === 'ArrowDown') setTarget(st.target - 10);
  if (e.key === 'ArrowRight') skip(250);
  if (e.key === 'ArrowLeft') skip(-250);
});
$('pwr').addEventListener('input', (e) => {
  st.target = +e.target.value;
});

// hide everything on screen, leaving only the ride: the button, the H key, or by voice. H, a click, or "show" brings it back.
export const setClean = (hide) => document.body.classList.toggle('clean', hide);
const isClean = () => document.body.classList.contains('clean');
$('clean').addEventListener('click', (e) => {
  e.stopPropagation();
  setClean(true);
});
addEventListener('click', () => {
  if (isClean()) setClean(false);
});
addEventListener('keydown', (e) => {
  if ((e.key === 'h' || e.key === 'H') && !e.metaKey && !e.ctrlKey && !e.altKey) setClean(!isClean());
});
$('skip').addEventListener('click', () => skip(250));
