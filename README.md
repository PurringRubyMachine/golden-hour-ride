# Golden Hour Ride

An indoor cycling ride that runs in the browser (Three.js). Ride an invented mountain valley, or a real road built from LiDAR survey data.

Live: https://purringrubymachine.github.io/golden-hour-ride/ · Leckhampton loop: https://purringrubymachine.github.io/golden-hour-ride/?course=leckhampton

This project is a fork of [jamiemarsland/golden-hour-ride](https://github.com/jamiemarsland/golden-hour-ride) by Jamie Marsland, who wrote the original ride. The fork is being refactored so it is easier to maintain and so anyone with a LiDAR terrain model can add their own course: see [docs/refactor-plan.md](docs/refactor-plan.md).

## What's in it

- Two courses: an invented mountain valley, and a real 11.9 km Leckhampton loop built from Environment Agency lidar, dressed as the 19th-century hill (sheep, hay stooks, quarry smoke).
- Four looks: Golden, Overcast, Rain and Mist. Buttons at the top, keys 1–4, or by voice.
- Skip forward and back 250 m with the arrow keys.
- Hide everything on screen for a clean view: the Hide info button, the H key, or say "hide". Press H, click, or say "show" to bring it back.
- Power from a slider, or from a Bluetooth trainer (Chrome or Edge). If the trainer supports resistance control (FTMS), the ride also sends it the road gradient, so climbs feel harder; the button shows "Trainer: power and gradient" or "Trainer: power only". The trainer feels half the road gradient by default; the − and + buttons beside the trainer button change that in steps of 10 %, from off to the full gradient, and the choice is kept in the browser (`?hills=` sets it for one visit). With voice on, say "easier" or "harder" to move it by 20 %, "flat" for off, or "full" for all of it. The last trainer is remembered: the button reads "Reconnect trainer" and rejoins it without the browser's device list where Chrome allows that, and a dropped connection is retried automatically.
- Descents count half in the speed model and the rider brakes above 54 km/h, so downhill speed stays sensible.

## Run it locally

The ride needs a local web server; opening `index.html` straight from disk does not work, because browsers block pages from reading local files.

```bash
python3 -m http.server 8791
```

Then open http://localhost:8791/.

## Development

There is no build step: the browser loads the files as they are. Node.js is used only for development tools.

```bash
npm install          # ESLint, Prettier and Playwright
npm test             # unit tests (Node's built-in test runner, under a second)
npm run lint
npm run format:check
npm run test:visual  # screenshot tests, about a minute: see tests/visual/README.md
```

Pushing to `main` publishes the ride to GitHub Pages (`.github/workflows/pages.yml`).

## Building a course

The course builder turns a GPX route and LiDAR DTM files (any format GDAL reads, in any coordinate system) into a course folder. It needs Python 3.10 or later.

```bash
python3 -m venv .venv
.venv/bin/pip install -r tools/requirements-dev.txt

.venv/bin/python -m tools.coursebuilder build --id my-loop --name "My Loop" \
    --route my-loop.gpx --dtm dtm/ \
    --heights-credit "Heights: <the DTM's source>" --heights-licence <its licence>
.venv/bin/python -m tools.coursebuilder validate
.venv/bin/pytest                        # the builder's tests, a few seconds
```

For a route in England, `fetch-ea --route my-loop.gpx --out dtm/` downloads Environment Agency LiDAR for it and prints the credit options to use. `build --help` lists the rest: pastoral scenery, smoke, the start point, and turning off OpenStreetMap features. A full walkthrough is coming in phase 5 of `docs/refactor-plan.md`.

## Layout

- `index.html` – the page: controls, display and the import map for Three.js.
- `src/` – the ride, as ES modules. `main.js` loads the textures and course, then `scene.js` builds the scene, one module per part:
  - `course/` – loading and checking a course, the road line and the ground
  - `scenery/` – road surface, grass, trees, buildings, clouds and the rest
  - `render/` – renderer, textures, sky and post-processing
  - `devices/` – smart trainers (FTMS)
  - `ui/` – controls, course menu, ride log and voice
  - `physics.js` – the speed model; `weather.js`; `ride.js` – the frame loop
- `styles/` – the page's CSS.
- `courses/` – one folder per course; `index.json` lists them for the menu. The format is described in `docs/refactor-plan.md` (course format, version 1).
- `assets/` – textures.
- `tests/` – unit tests (`unit/`) and screenshot tests (`visual/`).
- `tools/coursebuilder/` – the course builder: a GPX route and LiDAR DTM files in, a course folder out (see below).
- `docs/` – plans and design notes.

## Credits

- Original ride: Jamie Marsland.
- Textures: Poly Haven (CC0).
- Terrain: Environment Agency LiDAR Composite DTM, Open Government Licence v3.0.
- Roads, woodland and field boundaries: © OpenStreetMap contributors, ODbL.
- 3D engine: Three.js (MIT), loaded from jsDelivr.

## Licence

The code is released under the MIT licence: see `LICENSE`. Use it, change it, build your own ride.

The MIT licence covers the code only. The course data in `courses/leckhampton/` is derived from the sources credited above and stays under their terms: the Open Government Licence v3.0 for the terrain and the ODbL for the OpenStreetMap data. If you share or adapt that data, keep those credits.
