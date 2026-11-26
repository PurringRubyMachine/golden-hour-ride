// Frame rate and draw counts on this computer's real graphics chip. Run by hand: see README.md.
//
//   node tests/perf/measure.js [--courses valley,christmas,leckhampton] [--seconds 6] [--size 1920x1080] [--query quality=low]
//
// Opens each course in a visible Google Chrome window (headless Chrome won't use the real graphics chip on Linux), waits
// for the view to settle, then times the frames. Extra Chrome flags can be passed in CHROME_ARGS.
import { spawn } from 'node:child_process';
import { chromium } from '@playwright/test';

const arg = (name, fallback) => {
  const i = process.argv.indexOf('--' + name);
  return i > 0 ? process.argv[i + 1] : fallback;
};
const COURSES = {
  valley: '',
  christmas: 'theme=christmas',
  leckhampton: 'course=leckhampton',
  gatineau: 'course=gatineau-park-loop',
};
const courses = arg('courses', Object.keys(COURSES).join(',')).split(',');
const seconds = +arg('seconds', 6);
const [width, height] = arg('size', '1920x1080').split('x').map(Number);
const extra = arg('query', '');
const PORT = 8794;

const server = spawn('python3', ['-m', 'http.server', String(PORT)], { stdio: 'ignore' });
const browser = await chromium
  .launch({
    channel: 'chrome',
    headless: false,
    args: ['--ignore-gpu-blocklist', ...(process.env.CHROME_ARGS || '').split(' ').filter(Boolean)],
  })
  .catch((e) => {
    server.kill();
    throw e;
  });

const pad = (s, n) => String(s).padStart(n);
let first = true;
try {
  for (const name of courses) {
    if (!(name in COURSES)) throw new Error(`unknown course ${name}: try ${Object.keys(COURSES).join(', ')}`);
    const page = await browser.newPage({ viewport: { width, height } });
    page.on('pageerror', (e) => console.error(`${name}: page error: ${e.message}`));
    const query = [COURSES[name], extra].filter(Boolean).join('&');
    for (let tries = 0; ; tries++) {
      try {
        await page.goto(`http://localhost:${PORT}/?${query}`);
        break;
      } catch (e) {
        if (tries > 20) throw e; // the server may still be starting
        await new Promise((r) => setTimeout(r, 250));
      }
    }
    await page.waitForFunction(() => window.ride?.frame > 30 && window.ride.pending === 0, null, {
      timeout: 180_000,
    });
    const r = await page.evaluate(async (seconds) => {
      await new Promise((done) => setTimeout(done, 2000)); // let the start settle
      const times = [];
      const end = performance.now() + seconds * 1000;
      await new Promise((done) => {
        const step = (t) => {
          times.push(t);
          if (t < end) requestAnimationFrame(step);
          else done();
        };
        requestAnimationFrame(step);
      });
      const gaps = times
        .slice(1)
        .map((t, i) => t - times[i])
        .sort((a, b) => a - b);
      const gl = document.createElement('canvas').getContext('webgl2');
      const info = gl.getExtension('WEBGL_debug_renderer_info');
      return {
        gpu: info ? gl.getParameter(info.UNMASKED_RENDERER_WEBGL) : 'unknown',
        fps: gaps.length / ((times.at(-1) - times[0]) / 1000),
        median: gaps[gaps.length >> 1],
        p95: gaps[Math.floor(gaps.length * 0.95)],
        worst: gaps.at(-1),
        ...window.ride.stats,
      };
    }, seconds);
    if (first) {
      console.log(`${r.gpu}\n${width} x ${height}, pixel ratio ${await page.evaluate(() => devicePixelRatio)}`);
      console.log(
        `${'course'.padEnd(12)} ${pad('fps', 6)} ${pad('median', 8)} ${pad('95%', 8)} ${pad('worst', 8)} ${pad('calls', 6)} ${pad('triangles', 11)}  quality`,
      );
      first = false;
    }
    console.log(
      `${name.padEnd(12)} ${pad(r.fps.toFixed(1), 6)} ${pad(r.median.toFixed(1), 6)}ms ${pad(r.p95.toFixed(1), 6)}ms ${pad(r.worst.toFixed(0), 6)}ms ${pad(r.calls, 6)} ${pad(r.triangles.toLocaleString('en'), 11)}  ${r.quality}`,
    );
    await page.close();
  }
} finally {
  await browser.close();
  server.kill();
}
