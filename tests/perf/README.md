# Performance measurements

`measure.js` times the ride on this computer's real graphics chip and counts what each frame draws. It is run by hand, not in CI: CI machines have no graphics chip. Run it for changes to scenery or rendering, and give the numbers in the pull request.

```bash
node tests/perf/measure.js                          # all three courses, 1920 x 1080
node tests/perf/measure.js --courses leckhampton --seconds 10
node tests/perf/measure.js --query quality=low      # anything else for the address bar
```

It needs Google Chrome installed, and opens visible windows for a few seconds each: headless Chrome won't use the real graphics chip on Linux.

```
Mesa Intel(R) UHD Graphics (CML GT2)
1920 x 1080, pixel ratio 1
course          fps   median      95%    worst  calls   triangles  quality
valley          8.6   16.7ms  850.0ms    900ms     43   7,666,874  high
```

- **fps**, **median**, **95%** and **worst** are from the times between frames. A smooth ride has a median and 95% near 16.7 ms (60 fps) and no long worst frame.
- **calls** and **triangles** are for the last frame, all passes together: the shadow map, the scene and the post-processing. The same numbers are in `window.ride.stats` in the browser console.
- **quality** is the level the ride was on at the end. Without `--query quality=...` it is on Auto, which may step down during the run, so give a level when comparing changes.

Built-in graphics (Intel, AMD's Radeon Graphics) are the ones that matter: most riders have them. A frame budget of about 1.5 million triangles keeps the Medium quality level smooth there.

## Laptops with two graphics chips

On a laptop with built-in graphics and an NVIDIA card, Chrome normally uses the built-in chip. To measure on the NVIDIA card on Linux:

```bash
__NV_PRIME_RENDER_OFFLOAD=1 __GLX_VENDOR_LIBRARY_NAME=nvidia CHROME_ARGS=--ozone-platform=x11 node tests/perf/measure.js
```

The first line of the output names the chip that was used.
