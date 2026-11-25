// Shader uniforms shared between parts of the scene.
import * as THREE from 'three';

/* ---------- shader uniforms shared between parts of the scene ---------- */
export const uTime = { value: 0 }, uCloud = { value: 1 }, uMote = { value: 1 }, uMeadow = { value: new THREE.Vector2() }, uSunAmt = { value: 1 };
export const uRain = { value: 0 };                                                                    // how wet: 0 dry, 1 raining
export const uPx = { value: innerHeight * Math.min(devicePixelRatio, 2) / (2 * Math.tan(0.6)) };      // metres to pixels at 1 m
