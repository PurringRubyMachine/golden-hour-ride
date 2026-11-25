// Christmas lights.
import * as THREE from 'three';
import { rnd } from '../util/random.js';
import { uTime } from '../uniforms.js';
import { scene } from '../render/renderer.js';
import { st0 } from '../course/course.js';
import { xl } from './chalets.js';

if (xl.p.length) {
  // every Christmas light is one glowing point; bright enough to bloom
  const g = new THREE.BufferGeometry(),
    n = xl.p.length / 3,
    ph = new Float32Array(n);
  for (let i = 0; i < n; i++) ph[i] = rnd();
  g.setAttribute('position', new THREE.Float32BufferAttribute(xl.p, 3));
  g.setAttribute('aCol', new THREE.Float32BufferAttribute(xl.c, 3));
  g.setAttribute('aPh', new THREE.BufferAttribute(ph, 1));
  const lights = new THREE.Points(
    g,
    new THREE.ShaderMaterial({
      transparent: true,
      depthWrite: false,
      blending: THREE.AdditiveBlending,
      uniforms: { uTime, uPx: { value: (innerHeight * Math.min(devicePixelRatio, 2)) / (2 * Math.tan(0.6)) } },
      vertexShader: `uniform float uTime, uPx; attribute vec3 aCol; attribute float aPh; varying vec3 vCol;
      void main(){
        vec4 mv = viewMatrix * vec4(position, 1.); gl_Position = projectionMatrix * mv;
        float d = -mv.z, tw = 0.8 + 0.2 * sin(uTime * (1.2 + aPh * 2.5) + aPh * 40.);
        float px = 0.62 * uPx / d; gl_PointSize = clamp(px, 3., 30.);
        vCol = aCol * tw * (1. - smoothstep(450., 1100., d)) * min(1., px / 3.);
      }`,
      fragmentShader:
        'varying vec3 vCol; void main(){ float r = length(gl_PointCoord - 0.5); gl_FragColor = vec4(vCol * (pow(smoothstep(0.5, 0.0, r), 2.) * 5. + smoothstep(0.2, 0.0, r) * 30.), 1.); }',
    }),
  );
  lights.frustumCulled = false;
  lights.renderOrder = 4;
  scene.add(lights);
  st0.lights = n;
}
