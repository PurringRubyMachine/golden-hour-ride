// Sky, sun, haze and the light they cast.
import * as THREE from 'three';
import { Sky } from 'three/addons/objects/Sky.js';
import { XMAS } from '../options.js';
import { renderer, scene } from './renderer.js';

const V3 = THREE.Vector3;

const SUN_ELEV = XMAS ? 4.5 : 11,
  SUN_AZ = -24;
export const sunDir = new V3().setFromSphericalCoords(
  1,
  THREE.MathUtils.degToRad(90 - SUN_ELEV),
  THREE.MathUtils.degToRad(SUN_AZ),
);
export const sunFlat = new V3(sunDir.x, 0, sunDir.z).normalize();

export const sky = new Sky();
sky.scale.setScalar(450000);
Object.assign(sky.material.uniforms.turbidity, { value: XMAS ? 5 : 7 });
Object.assign(sky.material.uniforms.rayleigh, { value: XMAS ? 3.2 : 2.2 });
Object.assign(sky.material.uniforms.mieCoefficient, { value: 0.004 });
Object.assign(sky.material.uniforms.mieDirectionalG, { value: 0.82 });
sky.material.uniforms.sunPosition.value.copy(sunDir);

export const envScene = new THREE.Scene();
envScene.add(sky);
export const pmrem = new THREE.PMREMGenerator(renderer);
let envRT = pmrem.fromScene(envScene);
scene.environment = envRT.texture;
export function setEnvironment(rt) {
  envRT.dispose();
  envRT = rt;
  scene.environment = rt.texture;
} // the weather swaps in a new sky reflection

// Read the sky's own horizon colour so the haze melts into it.
function sampleSky(dir) {
  const rt = new THREE.WebGLRenderTarget(4, 4, { type: THREE.FloatType });
  const cam = new THREE.PerspectiveCamera(2, 1, 0.1, 10);
  cam.lookAt(dir);
  renderer.setRenderTarget(rt);
  renderer.render(envScene, cam);
  const px = new Float32Array(64);
  renderer.readRenderTargetPixels(rt, 0, 0, 4, 4, px);
  renderer.setRenderTarget(null);
  rt.dispose();
  const ok = isFinite(px[0]) && px[0] + px[1] + px[2] > 0.01;
  return ok ? new THREE.Color(px[0], px[1], px[2]) : new THREE.Color(0.9, 0.62, 0.42);
}
const hazeDir = new V3().setFromSphericalCoords(1, THREE.MathUtils.degToRad(88), THREE.MathUtils.degToRad(SUN_AZ + 55));
export const hazeCol = sampleSky(hazeDir);
scene.add(sky);
scene.fog = new THREE.FogExp2(hazeCol, 0.0007);

export const sun = new THREE.DirectionalLight(0xffb070, 10);
sun.castShadow = true;
sun.shadow.mapSize.set(4096, 4096);
Object.assign(sun.shadow.camera, { left: -110, right: 110, top: 110, bottom: -110, near: 1, far: 700 });
sun.shadow.bias = -0.0004;
sun.shadow.normalBias = 0.6;
scene.add(sun, sun.target);
export const hemi = new THREE.HemisphereLight(XMAS ? 0xa6b4ea : 0xa9b8ee, XMAS ? 0x9aa2b6 : 0x6b563a, 2.2);
scene.add(hemi);
