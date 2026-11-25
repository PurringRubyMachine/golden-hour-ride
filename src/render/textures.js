// Photo-scanned surface textures (Poly Haven, CC0).
import * as THREE from 'three';
import { $, canvas2d } from '../util/dom.js';
import { MAX_ANISO } from './renderer.js';

/* ---------- photo-scanned surfaces (Poly Haven, CC0) ---------- */
const loadImg = src => new Promise((res, rej) => { const i = new Image(); i.onload = () => res(i); i.onerror = () => rej(new Error('missing texture')); i.src = src; });
const TEX = ['asphalt_02_diff_2k', 'asphalt_02_nor_gl_2k', 'leafy_grass_diff_2k', 'leafy_grass_nor_gl_1k', 'rock_face_03_diff_1k', 'gravel_ground_01_diff_1k'];
const readable = img => { try { const [, g] = canvas2d(1, 1); g.drawImage(img, 0, 0, 1, 1); g.getImageData(0, 0, 1, 1); return true; } catch (e) { return false; } };
const imgs = await Promise.all(TEX.map(n => loadImg(`assets/${n}.jpg`))).catch(() => null);
if (!imgs || !readable(imgs[0])) {
  // Opened straight from disk, a browser won't let a page read image files, so the ride needs a web server.
  $('loading').textContent = location.protocol === 'file:' ? 'Run a local web server to ride: see the README' : 'Could not load the textures';
  throw new Error('ride: textures missing or unreadable');
}
export const [imgAsphalt, imgAsphaltN, imgGrass, imgGrassN, imgRock, imgGravel] = imgs;
export const imgTex = (img, srgb) => {
  const t = new THREE.Texture(img); t.wrapS = t.wrapT = THREE.RepeatWrapping;
  if (srgb) t.colorSpace = THREE.SRGBColorSpace;
  t.anisotropy = MAX_ANISO; t.needsUpdate = true; return t;
};
