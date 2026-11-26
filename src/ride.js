// The ride loop: speed, camera, and drawing each frame.
import * as THREE from 'three';
import { $ } from './util/dom.js';
import { smooth } from './util/noise.js';
import { FREEZE, SCENERY } from './options.js';
import { uMeadow, uTime } from './uniforms.js';
import { camera, renderer, scene } from './render/renderer.js';
import { sun, sunDir } from './render/sky.js';
import { LEN, at, mkPose } from './course/road.js';
import { chunks } from './scenery/grass.js';
import { rainU, setWeather, stepWeather, wx } from './weather.js';
import { drawHeadUnit, rig } from './cockpit.js';
import { composer, lens, rays } from './render/post.js';
import { nextSpeed } from './physics.js';
import { st } from './state.js';
import { setClean } from './ui/controls.js';
import { audio } from './audio.js';
import { XMAS } from './course/course.js';
import { onQuality, quality, qualityFrame } from './render/quality.js';
import { nearTrees } from './scenery/trees.js';

const V3 = THREE.Vector3;

const LANE = -1.75,
  clock = new THREE.Clock();
const pose = mkPose(),
  ahead = mkPose(),
  probe = mkPose(),
  look = new V3(),
  sunNdc = new V3(),
  fwd = new V3();
let lean = 0,
  phase = 0,
  huT = 0,
  first = true;
// scenery mode's weather, in order, and how many seconds each one stays
const SCENE_PLAN = XMAS
  ? [
      ['snow', 280],
      ['mist', 100],
      ['snow', 180],
      ['golden', 95],
    ]
  : [
      ['golden', 200],
      ['mist', 110],
      ['rain', 130],
      ['overcast', 70],
      ['golden', 90],
    ];
let scene_t = 0,
  scene_i = 0;
if (SCENERY !== null) {
  setClean(true);
  st.target = st.power = 90;
  if (SCENERY === 'nobars') rig.visible = false;
}

// count what each frame draws across all its passes (shadows, scene, post-processing), for window.ride.stats
renderer.info.autoReset = false;

// how far the verge grass is drawn: patches are built within this distance and dropped 100 m beyond it
let verge = 230;
onQuality((q) => (verge = q.verge));
let last = performance.now();

function tick() {
  renderer.info.reset();
  const now = performance.now();
  qualityFrame(now - last, now);
  last = now;
  const dt = FREEZE ? 0 : Math.min(clock.getDelta(), 0.05);
  uTime.value += dt;

  // power -> speed: gravity, rolling resistance and air drag
  st.power += (st.target - st.power) * Math.min(1, dt * 3);
  at(st.s, pose);
  const v = st.v;
  st.v = nextSpeed(v, st.power, pose.t.y, dt);
  if (SCENERY !== null) {
    st.v = v + (5 - v) * Math.min(1, dt); // a steady 18 km/h, whatever the gradient
    scene_t += dt;
    if (scene_t >= SCENE_PLAN[scene_i][1]) {
      scene_t = 0;
      scene_i = (scene_i + 1) % SCENE_PLAN.length;
      setWeather(SCENE_PLAN[scene_i][0]);
    }
  }
  st.s = (st.s + st.v * dt) % LEN;
  st.dist += st.v * dt;
  st.grade += (pose.t.y * 100 - st.grade) * Math.min(1, dt * 2);

  // camera: follow the lane, look down the road, lean into bends, rock with the pedals
  at(st.s, pose);
  at(st.s + 9, ahead);
  at(st.s + 4, probe);
  uMeadow.value.set(pose.p.x + pose.t.x * 78, pose.p.z + pose.t.z * 78); // most of the meadow sits in front of you
  const kappa = -(pose.t.z * probe.t.x - pose.t.x * probe.t.z) / 4;
  lean += (Math.atan((st.v * st.v * kappa) / 9.81) * 0.55 - lean) * Math.min(1, dt * 3);
  const effort = Math.min(1, st.power / 300);
  phase += (dt * Math.PI * 2 * (st.power > 5 ? 60 + Math.min(40, st.power / 8) : 0)) / 60;
  const sway = Math.sin(phase);
  camera.position.copy(pose.p).addScaledVector(pose.r, LANE + sway * 0.004 * effort);
  camera.position.y += 1.52;
  look.copy(ahead.p).addScaledVector(ahead.r, LANE);
  look.y += 0.3;
  camera.lookAt(look);
  camera.rotateZ(-lean);
  const fov = 62 + Math.min(st.v, 20) * 0.75;
  if (Math.abs(fov - camera.fov) > 0.01) {
    camera.fov = fov;
    camera.updateProjectionMatrix();
  }

  stepWeather(dt);
  rainU.uVel.value.copy(pose.t).multiplyScalar(st.v);

  // sun shadow box travels with the rider, pushed forward into the view
  sun.target.position.copy(pose.p).addScaledVector(pose.t, 70);
  sun.position.copy(sun.target.position).addScaledVector(sunDir, 350);
  let built = false,
    pending = 0;
  for (const c of chunks) {
    const d2 = c.c.distanceToSquared(camera.position);
    // one patch per frame keeps the ride smooth; with ?freeze, build them all at once (same order, so the same grass)
    if (d2 < verge * verge) {
      if (!c.mesh) {
        if (!built || FREEZE) {
          c.mesh = c.build();
          built = true;
        } else pending++;
      }
    } else if (c.mesh && d2 > (verge + 100) ** 2) {
      scene.remove(c.mesh);
      c.mesh.dispose();
      c.mesh = null;
    }
  }
  st.pending = pending;
  nearTrees(camera.position);

  sunNdc.copy(camera.position).addScaledVector(sunDir, 1000).project(camera);
  rays.uniforms.uSunUv.value.set(sunNdc.x * 0.5 + 0.5, sunNdc.y * 0.5 + 0.5);
  rays.uniforms.uAmt.value = 0.25 * wx.rays * smooth(0.1, 0.6, camera.getWorldDirection(fwd).dot(sunDir));
  lens.uniforms.uSpeed.value = Math.min(1, st.v / 22);
  lens.uniforms.uTime.value = uTime.value;
  lens.uniforms.uRain.value = wx.rain;
  if (audio) {
    const t = audio.ac.currentTime;
    audio.wind.g.gain.setTargetAtTime(Math.min(0.5, ((st.v * st.v) / 400) * 0.35), t, 0.2);
    audio.wind.f.frequency.setTargetAtTime(300 + st.v * 40, t, 0.2);
    audio.tyre.g.gain.setTargetAtTime(Math.min(0.35, (st.v / 15) * 0.25), t, 0.2);
    audio.rain.g.gain.setTargetAtTime(wx.rain * 0.1, t, 0.4);
  }

  huT -= dt;
  if (huT <= 0) {
    huT = 0.25;
    drawHeadUnit(st.v * 3.6, st.power);
    $('h-pw').textContent = st.power.toFixed(0);
    $('h-sp').textContent = (st.v * 3.6).toFixed(1);
    $('h-gr').textContent = (st.grade >= 0 ? '+' : '') + st.grade.toFixed(1);
    $('h-di').textContent = (st.dist / 1000).toFixed(2);
  }

  composer.render();
  st.stats.calls = renderer.info.render.calls;
  st.stats.triangles = renderer.info.render.triangles;
  st.stats.quality = quality.level;
  st.frame++;
  if (first) {
    first = false;
    $('loading').style.opacity = 0;
    setTimeout(() => $('loading').remove(), 900);
  }
  // ?freeze: once the view is complete, stop drawing, so a screenshot is not competing with the next frame
  if (FREEZE && st.pending === 0 && st.frame > 2) {
    st.held = true;
    return;
  }
  requestAnimationFrame(tick);
}
// for tests: move to a distance along the road and draw again (with ?freeze, drawing stops once the view is complete)
st.go = (s) => {
  st.s = ((s % LEN) + LEN) % LEN;
  if (st.held) {
    st.held = false;
    requestAnimationFrame(tick);
  }
};
tick();
