// Smart trainer connection: power in, gradient out.
import { $ } from '../util/dom.js';
import { OPTIONS } from '../options.js';
import { st } from '../state.js';
import { setTarget } from '../ui/controls.js';
import { FTMS, FTMS_POINT, OP_CONTROL, ftmsAsk, simParams, trainerGrade } from './ftms.js';

/* Smart trainer. Power is read from the Cycling Power service. If the trainer also has the Fitness Machine
   Service (FTMS), the game takes control of it and sends the road gradient, so climbs feel harder on the bike.
   Without FTMS, or if the trainer refuses control, it stays power only. */

const bike = { dev: null, known: null, point: null, busy: false, sent: 0, at: 0, fails: 0, timer: 0, tries: 0 };
// How much of the road's gradient the trainer is asked to feel. Half by default, like most indoor games,
// so a 10 % climb pedals like 5 %; descents count half again. ?hills=100 gives the full gradient, ?hills=0 none.
const HILLS_KEY = 'golden-hour-ride-hills'; // kept in this browser; ?hills= sets it for one visit
export let HILLS = (() => {
  const q = OPTIONS.hills;
  let n = 50;
  try {
    const k = localStorage.getItem(HILLS_KEY);
    if (k !== null && isFinite(+k)) n = +k;
  } catch {}
  if (q !== null && q !== '' && isFinite(+q)) n = +q;
  return Math.max(0, Math.min(100, n)) / 100;
})();
export const setHills = (pct) => {
  HILLS = Math.max(0, Math.min(100, Math.round(pct / 10) * 10)) / 100;
  try {
    localStorage.setItem(HILLS_KEY, String(Math.round(HILLS * 100)));
  } catch {}
  $('hval').textContent = HILLS ? 'Hills ' + Math.round(HILLS * 100) + ' %' : 'Hills off';
  bike.at = 0; // tell the trainer straight away
};
const TRAINER_KEY = 'golden-hour-ride-trainer'; // the last trainer used: { id, name }, kept in this browser
const lastTrainer = () => {
  try {
    return JSON.parse(localStorage.getItem(TRAINER_KEY)) || null;
  } catch {
    return null;
  }
};
const btLabel = () => {
  const last = lastTrainer();
  $('bt').textContent = bike.dev
    ? bike.point
      ? 'Trainer: power and gradient'
      : 'Trainer: power only'
    : bike.known || (last && navigator.bluetooth && navigator.bluetooth.getDevices)
      ? 'Reconnect trainer'
      : 'Connect trainer';
};
$('hless').addEventListener('click', () => setHills(HILLS * 100 - 10));
$('hmore').addEventListener('click', () => setHills(HILLS * 100 + 10));

// about once a second, or sooner when the gradient has moved by more than 0.5 %
async function sendGrade() {
  const now = performance.now(),
    g = trainerGrade(st.grade, HILLS),
    wait = now - bike.at;
  if (!bike.point || bike.busy || wait < 250 || (wait < 1000 && Math.abs(g - bike.sent) <= 0.5)) return;
  bike.busy = true;
  bike.at = now;
  const point = bike.point;
  try {
    await point.writeValueWithResponse(simParams(g));
    bike.sent = g;
    bike.fails = 0;
  } catch {
    // three misses in a row: give up on gradient and carry on with power only
    if (bike.point === point && ++bike.fails >= 3) {
      bike.point = null;
      clearInterval(bike.timer);
      btLabel();
    }
  }
  bike.busy = false;
}

async function ftmsStart(server) {
  try {
    const point = await (await server.getPrimaryService(FTMS)).getCharacteristic(FTMS_POINT);
    await point.startNotifications();
    await ftmsAsk(point, [OP_CONTROL]);
    Object.assign(bike, { point, busy: false, sent: 0, at: 0, fails: 0 });
    bike.timer = setInterval(sendGrade, 250);
  } catch {
    bike.point = null;
  } // no FTMS, or control not given: power only
}

// give up on a slow Bluetooth step instead of hanging on it
const within = (p, ms) =>
  new Promise((ok, no) => {
    const t = setTimeout(() => no(new Error('timed out')), ms);
    p.then(
      (v) => {
        clearTimeout(t);
        ok(v);
      },
      (e) => {
        clearTimeout(t);
        no(e);
      },
    );
  });
const watched = new WeakSet();

// connect to one trainer and start reading its power (and sending gradient, if it allows)
async function useTrainer(dev) {
  let server;
  try {
    server = await within(dev.gatt.connect(), 8000);
  } catch (err) {
    try {
      dev.gatt.disconnect();
    } catch {}
    throw err;
  }
  const svc = await server.getPrimaryService('cycling_power');
  const ch = await svc.getCharacteristic('cycling_power_measurement');
  await ch.startNotifications();
  ch.addEventListener('characteristicvaluechanged', (e) => {
    st.trainer = true;
    setTarget(e.target.value.getInt16(2, true));
  });
  if (!watched.has(dev)) {
    watched.add(dev);
    dev.addEventListener('gattserverdisconnected', () => {
      st.trainer = false;
      clearInterval(bike.timer);
      bike.dev = bike.point = null;
      btLabel();
      rejoin(dev);
    });
  }
  bike.dev = bike.known = dev;
  bike.tries = 0;
  $('bt').title = dev.name || '';
  try {
    localStorage.setItem(TRAINER_KEY, JSON.stringify({ id: dev.id, name: dev.name || '' }));
  } catch {}
  await ftmsStart(server);
  if (dev.gatt.connected) btLabel();
}

// the trainer dropped out (out of range, asleep, a blip): try it again a few times before giving up
async function rejoin(dev) {
  while (!bike.dev && bike.known === dev && bike.tries < 6) {
    bike.tries++;
    $('bt').textContent = 'Reconnecting…';
    await new Promise((r) => setTimeout(r, 2500));
    if (bike.dev || bike.known !== dev) return;
    try {
      await useTrainer(dev);
      return;
    } catch {
      clearInterval(bike.timer);
      bike.dev = bike.point = null;
    }
  }
  btLabel();
}

// trainers this browser already has permission for, the one used last first
async function knownTrainers() {
  const list = bike.known ? [bike.known] : [],
    last = lastTrainer();
  if (navigator.bluetooth.getDevices) {
    try {
      for (const d of await navigator.bluetooth.getDevices())
        if (!list.includes(d)) last && d.id === last.id ? list.unshift(d) : list.push(d);
    } catch {}
  }
  return list;
}

$('bt').addEventListener('click', async () => {
  if (!navigator.bluetooth) {
    $('bt').textContent = 'Needs Chrome or Edge';
    return;
  }
  if (bike.busyJoin) return;
  bike.busyJoin = true;
  bike.tries = 99; // a click takes over from any automatic retry
  try {
    if (!bike.dev) {
      for (const dev of await knownTrainers()) {
        $('bt').textContent = 'Reconnecting…';
        try {
          await useTrainer(dev);
          return;
        } catch {
          clearInterval(bike.timer);
          bike.dev = bike.point = null;
        }
      }
    }
    // nothing remembered, or it did not answer: show the browser's list of trainers nearby
    btLabel();
    const dev = await navigator.bluetooth.requestDevice({
      filters: [{ services: ['cycling_power'] }, { services: [FTMS] }],
      optionalServices: ['cycling_power', FTMS],
    });
    $('bt').textContent = 'Connecting…';
    if (bike.dev && bike.dev !== dev) {
      const old = bike.dev;
      bike.known = dev;
      try {
        old.gatt.disconnect();
      } catch {}
    }
    await useTrainer(dev);
  } catch {
    if (!bike.dev) {
      clearInterval(bike.timer);
      bike.point = null;
    }
    btLabel();
  } finally {
    bike.busyJoin = false;
  }
});
btLabel();
setHills(HILLS * 100);
