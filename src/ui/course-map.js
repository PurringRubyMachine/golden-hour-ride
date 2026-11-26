// The course map: the loop from above with the rider on it, the height profile, and where on the loop the rider is.
// The loop and profile are drawn once; only the rider's marks are redrawn as they move (updateMap, from ride.js).
import { $ } from '../util/dom.js';
import { LEN, N, P, at, mkPose } from '../course/road.js';
import { fit, profile, thin, whereOnLoop } from './map-geometry.js';

const W = 200,
  MAP_H = 130,
  PROF_H = 44,
  H = MAP_H + PROF_H,
  PAD = 10,
  LX = 34, // the profile starts here, leaving room for its height labels
  KEY = 'golden-hour-ride-map'; // '0' if the rider turned the map off, kept in this browser

const box = $('map'),
  btn = $('mapbtn'),
  label = document.createElement('div');
label.className = 'where';
const canvas = (cls) => {
  const c = document.createElement('canvas'),
    dpr = Math.min(devicePixelRatio || 1, 2);
  c.className = cls;
  c.width = W * dpr;
  c.height = H * dpr;
  c.style.width = W + 'px';
  c.style.height = H + 'px';
  const g = c.getContext('2d');
  g.scale(dpr, dpr);
  return [c, g];
};
const [base, bg] = canvas('base'),
  [over, og] = canvas('over');
box.append(base, over, label);

// the road every ~20 m: plenty for a 200-pixel map
const step = Math.max(1, Math.round(20 / (LEN / N)));
const idx = thin([...Array(N).keys()], step);
const toMap = fit(
  idx.map((i) => [P[i].x, P[i].z]),
  W,
  MAP_H,
  PAD,
);
const prof = profile(
  idx.map((i) => (i / N) * LEN),
  idx.map((i) => P[i].y),
  LEN,
  W - LX,
  PROF_H,
  6,
);

{
  // the loop: a light line on a dark edge, so it shows on any sky
  bg.lineJoin = bg.lineCap = 'round';
  const path = () => {
    bg.beginPath();
    idx.forEach((i, k) => bg[k ? 'lineTo' : 'moveTo'](...toMap([P[i].x, P[i].z])));
    bg.closePath();
  };
  path();
  bg.strokeStyle = 'rgba(0,0,0,0.45)';
  bg.lineWidth = 4.5;
  bg.stroke();
  path();
  bg.strokeStyle = 'rgba(255,244,228,0.9)';
  bg.lineWidth = 2;
  bg.stroke();
  // a tick across the road where the course begins
  const [sx, sy] = toMap([P[0].x, P[0].z]),
    rx = P[0].x + P[1].z - P[0].z,
    rz = P[0].z - (P[1].x - P[0].x); // a point beside the first, square to the road
  const [tx, ty] = toMap([rx, rz]),
    len = Math.hypot(tx - sx, ty - sy) || 1,
    ux = (tx - sx) / len,
    uy = (ty - sy) / len;
  bg.beginPath();
  bg.moveTo(sx - ux * 6, sy - uy * 6);
  bg.lineTo(sx + ux * 6, sy + uy * 6);
  bg.strokeStyle = '#fff';
  bg.lineWidth = 2;
  bg.stroke();

  // the profile: a filled hill line along the bottom, with the lowest and highest heights
  bg.translate(0, MAP_H);
  bg.fillStyle = 'rgba(255,255,255,0.7)';
  bg.font = '9px system-ui, sans-serif';
  bg.textBaseline = 'top';
  bg.fillText(`${Math.round(prof.hi)} m`, 0, 3);
  bg.textBaseline = 'bottom';
  bg.fillText(`${Math.round(prof.lo)} m`, 0, PROF_H - 3);
  bg.translate(LX, 0);
  bg.beginPath();
  bg.moveTo(0, PROF_H);
  for (const [x, y] of prof.points) bg.lineTo(x, y);
  bg.lineTo(W - LX, PROF_H);
  bg.closePath();
  bg.fillStyle = 'rgba(255,244,228,0.16)';
  bg.fill();
  bg.beginPath();
  prof.points.forEach(([x, y], k) => bg[k ? 'lineTo' : 'moveTo'](x, y));
  bg.strokeStyle = 'rgba(255,244,228,0.75)';
  bg.lineWidth = 1.2;
  bg.stroke();
  bg.setTransform(1, 0, 0, 1, 0, 0);
}

const pose = mkPose();
let lastS = NaN,
  lastText = '';
// the rider's marks: an arrow on the loop, a line and dot on the profile, and the distance
export function updateMap(s) {
  if (box.hidden || Math.abs(s - lastS) < 5) return; // 5 m is under a pixel on the map: redraw only when it shows
  lastS = s;
  const dpr = over.width / W;
  og.setTransform(dpr, 0, 0, dpr, 0, 0);
  og.clearRect(0, 0, W, H);
  at(s, pose);
  const [x, y] = toMap([pose.p.x, pose.p.z]),
    [ax, ay] = toMap([pose.p.x + pose.t.x, pose.p.z + pose.t.z]),
    a = Math.atan2(ay - y, ax - x);
  og.translate(x, y);
  og.rotate(a);
  og.beginPath();
  og.moveTo(7, 0);
  og.lineTo(-5, 4.5);
  og.lineTo(-2.5, 0);
  og.lineTo(-5, -4.5);
  og.closePath();
  og.fillStyle = '#ffb070';
  og.strokeStyle = 'rgba(0,0,0,0.6)';
  og.lineWidth = 1.5;
  og.stroke();
  og.fill();
  og.setTransform(dpr, 0, 0, dpr, 0, 0);
  const frac = (((s % LEN) + LEN) % LEN) / LEN,
    px = LX + frac * (W - LX),
    hy = prof.points[Math.min(prof.points.length - 1, Math.round(frac * (prof.points.length - 1)))][1];
  og.fillStyle = 'rgba(255,176,112,0.8)';
  og.fillRect(px - 0.75, MAP_H, 1.5, PROF_H);
  og.beginPath();
  og.arc(px, MAP_H + hy, 3, 0, Math.PI * 2);
  og.fillStyle = '#ffb070';
  og.fill();
  const text = whereOnLoop(s, LEN);
  if (text !== lastText) label.textContent = lastText = text;
}

// The Map button and the M key turn it off and on.
const show = (on) => {
  box.hidden = !on;
  btn.classList.toggle('on', on);
  try {
    localStorage.setItem(KEY, on ? '1' : '0');
  } catch {}
  lastS = NaN; // draw the marks straight away
};
let stored = null;
try {
  stored = localStorage.getItem(KEY);
} catch {}
show(stored !== '0');
btn.addEventListener('click', () => show(box.hidden));
addEventListener('keydown', (e) => {
  if ((e.key === 'm' || e.key === 'M') && !e.metaKey && !e.ctrlKey && !e.altKey) show(box.hidden);
});
