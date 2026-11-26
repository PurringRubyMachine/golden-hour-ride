// Christmas: chalets with lit windows, snow on the roof and smoke from the chimney.
import * as THREE from 'three';
import { canvas2d } from '../util/dom.js';
import { makeRandom } from '../util/random.js';
import { uPx, uTime } from '../uniforms.js';
import { MAX_ANISO, scene } from '../render/renderer.js';
import { XMAS, st0 } from '../course/course.js';
import { N, P, R, T } from '../course/road.js';
import { meshH } from '../course/terrain.js';

const V3 = THREE.Vector3;
const rnd = makeRandom('chalets');

export const chalets = [],
  xl = { p: [], c: [] },
  XL_COLS = [
    [1, 0.62, 0.25],
    [1, 0.12, 0.08],
    [0.15, 0.9, 0.25],
    [0.2, 0.4, 1],
    [1, 0.75, 0.1],
  ];
if (XMAS) {
  const m4 = new THREE.Matrix4(),
    q = new THREE.Quaternion(),
    up = new V3(0, 1, 0),
    sc = new V3(),
    ps = new V3();
  const [wc, wg] = canvas2d(256, 128),
    [ec, eg] = canvas2d(256, 128);
  wg.fillStyle = '#3d2a1c';
  wg.fillRect(0, 0, 256, 128);
  for (let y = 0; y < 128; y += 9) {
    wg.fillStyle = `rgba(${(20 + rnd() * 30) | 0},${(12 + rnd() * 16) | 0},8,0.55)`;
    wg.fillRect(0, y, 256, 1.5);
    wg.fillStyle = `rgba(110,78,48,${rnd() * 0.25})`;
    wg.fillRect(0, y + 2, 256, 6);
  }
  wg.fillStyle = '#8d8a84';
  wg.fillRect(0, 100, 256, 28); // stone footing
  for (let i = 0; i < 260; i++) {
    const l = (110 + rnd() * 60) | 0;
    wg.fillStyle = `rgba(${l},${l},${l + 4},0.6)`;
    wg.fillRect(rnd() * 256, 100 + rnd() * 28, 5 + rnd() * 9, 3 + rnd() * 5);
  }
  eg.fillStyle = '#000';
  eg.fillRect(0, 0, 256, 128);
  for (const x of [44, 128, 212]) {
    wg.fillStyle = '#e9e2d0';
    wg.fillRect(x - 21, 34, 42, 46);
    wg.fillStyle = '#f6c877';
    wg.fillRect(x - 17, 38, 34, 38);
    wg.fillStyle = '#e9e2d0';
    wg.fillRect(x - 1, 38, 2, 38);
    wg.fillRect(x - 17, 56, 34, 2);
    wg.fillStyle = '#dfe6f2';
    wg.fillRect(x - 24, 80, 48, 5); // snow on the sill
    const gr = eg.createRadialGradient(x, 60, 2, x, 57, 30);
    gr.addColorStop(0, '#ffd28a');
    gr.addColorStop(1, '#c9781e');
    eg.fillStyle = gr;
    eg.fillRect(x - 17, 38, 34, 38);
    eg.fillStyle = '#000';
    eg.fillRect(x - 1, 38, 2, 38);
    eg.fillRect(x - 17, 56, 34, 2);
  }
  const tex = (c) => {
    const t = new THREE.CanvasTexture(c);
    t.colorSpace = THREE.SRGBColorSpace;
    t.anisotropy = MAX_ANISO;
    return t;
  };
  const wallMat = new THREE.MeshStandardMaterial({
    map: tex(wc),
    emissiveMap: tex(ec),
    emissive: 0xffffff,
    emissiveIntensity: 7,
    roughness: 0.95,
  });
  const box = new THREE.BoxGeometry(1, 1, 1).translate(0, 0.5, 0);
  // a gable roof with deep eaves: two snowy slopes, and the timber gable ends under them
  const rp = [],
    rc = [],
    snowC = [0.74, 0.78, 0.86],
    wood = [0.2, 0.13, 0.08],
    tri = (a, b, c, col) => {
      rp.push(...a, ...b, ...c);
      rc.push(...col, ...col, ...col);
    };
  const E = 0.62,
    O = 0.58,
    RY = 1; // eave reach, gable overhang, ridge height (all scaled per chalet)
  for (const sgn of [-1, 1]) {
    const e1 = [-O, 0, sgn * E],
      e2 = [O, 0, sgn * E],
      r1 = [-O, RY, 0],
      r2 = [O, RY, 0];
    sgn < 0 ? (tri(e1, r1, r2, snowC), tri(e1, r2, e2, snowC)) : (tri(e1, r2, r1, snowC), tri(e1, e2, r2, snowC));
    const gx = sgn * 0.5;
    tri([gx, 0, -0.5], [gx, 0, 0.5], [gx, 0.8, 0], wood);
    tri([gx, 0, 0.5], [gx, 0, -0.5], [gx, 0.8, 0], wood);
  }
  const roofGeo = new THREE.BufferGeometry();
  roofGeo.setAttribute('position', new THREE.Float32BufferAttribute(rp, 3));
  roofGeo.setAttribute('color', new THREE.Float32BufferAttribute(rc, 3));
  roofGeo.computeVertexNormals();
  const WANT = 14,
    walls = new THREE.InstancedMesh(box, wallMat, WANT),
    roofs = new THREE.InstancedMesh(
      roofGeo,
      new THREE.MeshStandardMaterial({ vertexColors: true, roughness: 1, side: THREE.DoubleSide }),
      WANT,
    );
  const stacks = new THREE.InstancedMesh(box, new THREE.MeshStandardMaterial({ color: 0x77726b, roughness: 1 }), WANT),
    smokeAt = [];
  let n = 0;
  for (let k = 0; k < WANT * 6 && n < WANT; k++) {
    const i = Math.floor(((k + 0.2 + rnd() * 0.6) / (WANT * 6)) * N) % N,
      side = rnd() < 0.5 ? -1 : 1,
      d = 21 + rnd() * 17;
    const x = P[i].x + R[i].x * side * d,
      z = P[i].z + R[i].z * side * d,
      y = meshH(x, z);
    if (Math.abs(y - P[i].y) > 8 || chalets.some((c) => (c[0] - x) ** 2 + (c[1] - z) ** 2 < 140 * 140)) continue;
    const slope = Math.hypot(meshH(x + 5, z) - meshH(x - 5, z), meshH(x, z + 5) - meshH(x, z - 5)) / 10;
    if (slope > 0.4) continue;
    const w = 9 + rnd() * 4,
      dp = 6.5 + rnd() * 2,
      h = 3.9 + rnd() * 0.8,
      a = Math.atan2(-T[i].z, T[i].x),
      lo = y - slope * 6 - 0.3;
    q.setFromAxisAngle(up, a);
    walls.setMatrixAt(n, m4.compose(ps.set(x, lo, z), q, sc.set(w, h + (y - lo), dp)));
    const top = y + h,
      rh = dp * 0.36;
    roofs.setMatrixAt(n, m4.compose(ps.set(x, top, z), q, sc.set(w, rh, dp)));
    const ca = Math.cos(a),
      sa = Math.sin(a),
      cx = x + ca * w * 0.25,
      cz = z - sa * w * 0.25;
    stacks.setMatrixAt(n, m4.compose(ps.set(cx, top + rh * 0.45, cz), q, sc.set(0.8, rh * 0.9 + 0.5, 0.8)));
    smokeAt.push([cx, top + rh * 1.35 + 0.5, cz]);
    for (const sgn of [-1, 1])
      for (let t = 0; t <= 1.001; t += 1 / 26) {
        // a string of warm lights under each eave
        const lx = (t - 0.5) * w * 1.14,
          lz = sgn * dp * 0.6;
        xl.p.push(x + ca * lx + sa * lz, top + 0.02 - 0.12 * Math.sin(t * Math.PI * 6) ** 2, z - sa * lx + ca * lz);
        xl.c.push(...XL_COLS[0]);
      }
    chalets.push([x, z]);
    n++;
  }
  walls.count = roofs.count = stacks.count = n;
  for (const m of [walls, roofs, stacks]) {
    m.castShadow = true;
    m.receiveShadow = true;
    m.frustumCulled = false;
    scene.add(m);
  }
  const PUFFS = 26,
    sp = new Float32Array(n * PUFFS * 3),
    ph = new Float32Array(n * PUFFS);
  smokeAt.forEach((p, k) => {
    for (let i = 0; i < PUFFS; i++) {
      sp.set(p, (k * PUFFS + i) * 3);
      ph[k * PUFFS + i] = rnd();
    }
  });
  const sg = new THREE.BufferGeometry();
  sg.setAttribute('position', new THREE.BufferAttribute(sp, 3));
  sg.setAttribute('aPh', new THREE.BufferAttribute(ph, 1));
  const smoke = new THREE.Points(
    sg,
    new THREE.ShaderMaterial({
      transparent: true,
      depthWrite: false,
      uniforms: {
        uTime,
        uPx,
        uCol: { value: new V3(0.5, 0.52, 0.6) },
      },
      vertexShader: `uniform float uTime, uPx; attribute float aPh; varying float vA;
      void main(){
        float age = fract(uTime * 0.07 + aPh);
        vec3 p = position + vec3(1.6, 0., 0.9) * age * 9. + vec3(sin(aPh * 40. + age * 5.) * 0.8 * age, age * 9. + age * age * 5., cos(aPh * 31. + age * 4.) * 0.8 * age);
        vec4 mv = viewMatrix * vec4(p, 1.); gl_Position = projectionMatrix * mv;
        gl_PointSize = (0.7 + age * 4.5) * uPx / -mv.z;
        vA = smoothstep(0., 0.1, age) * (1. - age) * 0.35;
      }`,
      fragmentShader:
        'uniform vec3 uCol; varying float vA; void main(){ float r = length(gl_PointCoord - 0.5); gl_FragColor = vec4(uCol, smoothstep(0.5, 0.1, r) * vA); }',
    }),
  );
  smoke.frustumCulled = false;
  smoke.renderOrder = 3;
  scene.add(smoke);
  st0.chalets = n;
}
