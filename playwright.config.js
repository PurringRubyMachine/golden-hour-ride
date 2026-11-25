import { defineConfig } from '@playwright/test';

// Screenshot tests: see tests/visual/README.md.
export default defineConfig({
  testDir: 'tests/visual',
  // Baselines are per platform: font rendering differs between operating systems.
  snapshotPathTemplate: '{testDir}/screenshots/{platform}/{arg}{ext}',
  // Software rendering is slow (several seconds of GPU work per frame), so be generous.
  timeout: 15 * 60_000,
  // Exact match: software rendering gives the same pixels on every run, so any change shows.
  expect: { timeout: 5 * 60_000, toHaveScreenshot: { threshold: 0, maxDiffPixels: 0 } },
  fullyParallel: true,
  workers: 3,
  reporter: [['list'], ['html', { open: 'never' }]],
  use: {
    baseURL: 'http://localhost:8793/',
    viewport: { width: 960, height: 540 },
    deviceScaleFactor: 1,
    // SwiftShader, Chrome's software GPU, gives the same pixels on every run, unlike real graphics cards and drivers.
    launchOptions: { args: ['--use-angle=swiftshader', '--enable-unsafe-swiftshader'] },
  },
  webServer: {
    command: 'python3 -m http.server 8793',
    url: 'http://localhost:8793/',
    reuseExistingServer: !process.env.CI,
  },
});
