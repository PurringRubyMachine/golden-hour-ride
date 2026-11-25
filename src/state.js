// The ride state, shared with the controls and the tests (window.ride).
import { AT } from './options.js';
import { hazeCol } from './render/sky.js';
import { real, st0 } from './course/course.js';
import { LEN, N, P } from './course/road.js';
import { setWeather } from './weather.js';

/* ---------- input: keys, slider, smart trainer ---------- */
const START = real ? 850 : 0;          // Leckhampton: begin on the lane about 150 m below where the hill steepens, not out in the vale

// frame: frames drawn so far; pending: verge grass near the rider still to be built (one patch is built per frame)
export const st = { s: isFinite(AT) ? AT : START, v: 6, power: 220, target: 220, dist: 0, trainer: false, frame: 0, pending: 0, grade: 0 };
window.ride = st; st.haze = hazeCol; st.built = st0; st.length = LEN;
st.goNear = (x, z) => { let b = 0, bd = 1e12; for (let i = 0; i < N; i++) { const d = (P[i].x - x) ** 2 + (P[i].z - z) ** 2; if (d < bd) { bd = d; b = i; } } st.s = Math.max(0, b * LEN / N - 60); return Math.round(Math.sqrt(bd)); };   // for checking: ride to the road nearest a point
st.weather = (n, i) => setWeather(n, i);
