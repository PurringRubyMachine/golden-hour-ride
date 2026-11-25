// The ride log: distance ridden, kept in this browser.
import { $ } from '../util/dom.js';
import { COURSE } from '../options.js';
import { st } from '../state.js';

/* ---------- ride log: distance ridden, kept in this browser (localStorage) ---------- */
{
  const KEY = 'golden-hour-ride-log', MIN = 100;         // rides under 100 m are not kept
  const load = () => { try { const a = JSON.parse(localStorage.getItem(KEY)); return Array.isArray(a) ? a : []; } catch { return []; } };
  const ride = { t: new Date().toISOString(), c: COURSE, m: 0, s: 0 };
  let last = performance.now(), ok = true;
  const save = () => {
    const now = performance.now();
    if (!document.hidden) ride.s += Math.min(10, (now - last) / 1000);
    last = now; ride.m = Math.round(st.dist);
    if (ride.m < MIN) return;
    const all = load().filter(r => r.t !== ride.t); all.push({ ...ride, s: Math.round(ride.s) });
    try { localStorage.setItem(KEY, JSON.stringify(all.slice(-300))); ok = true; } catch { ok = false; }
  };
  const km = m => (m / 1000).toFixed(m < 99950 ? 1 : 0), box = $('log'), btn = $('logbtn');
  const day = t => new Date(t).toLocaleDateString(undefined, { day: 'numeric', month: 'short' });
  const mins = s => s < 3600 ? Math.round(s / 60) + ' min' : Math.floor(s / 3600) + ' h ' + Math.round(s % 3600 / 60) + ' min';
  const draw = () => {
    const all = load().filter(r => r.t !== ride.t); if (st.dist >= MIN) all.push({ ...ride, m: Math.round(st.dist) });
    const today = new Date().toDateString(), sum = f => all.filter(f).reduce((a, r) => a + r.m, 0);
    const rows = all.slice(-10).reverse().map(r => `<tr><td>${day(r.t)}</td><td class="muted">${r.c === 'leckhampton' ? 'Leckhampton' : 'Alps'}</td><td class="muted">${mins(r.s)}</td><td>${km(r.m)} km</td></tr>`).join('');
    box.innerHTML = `<h3>Ride log</h3><div class="tot"><div><b>${km(sum(r => new Date(r.t).toDateString() === today))}</b><span>km today</span></div>` +
      `<div><b>${km(sum(() => true))}</b><span>km in total</span></div><div><b>${all.length}</b><span>rides</span></div></div>` +
      (rows ? `<table>${rows}</table>` : `<div class="muted">Rides appear here after the first 100 m.</div>`) +
      (ok ? '' : `<div class="muted" style="margin-top:8px">This browser is not letting the page save, so the log will not be kept.</div>`) +
      (all.length ? `<button id="logclear">Clear log</button>` : '');
    const c = $('logclear'); if (c) c.onclick = () => { if (confirm('Delete the whole ride log from this browser?')) { try { localStorage.removeItem(KEY); } catch {} st.dist = 0; ride.s = 0; draw(); } };
  };
  btn.onclick = () => { box.hidden = !box.hidden; btn.classList.toggle('on', !box.hidden); if (!box.hidden) draw(); };
  setInterval(() => { save(); if (!box.hidden) draw(); }, 5000);
  addEventListener('pagehide', save);
  document.addEventListener('visibilitychange', save);
}

