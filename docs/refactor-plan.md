# Refactor plan: a maintainable codebase with user-contributed courses

Status: draft for review · 2026-11-25

## Goals

1. Anyone with a GPX route and a LiDAR DTM covering it can build a course with one command, and add it to the ride without touching application code.
2. The codebase is something a professional developer can read, test and extend: modules with clear responsibilities, linting, automated tests, CI, contributor docs.
3. Nothing a rider sees gets worse. The ride looks and behaves the same after each phase unless a change is deliberate and noted.

## Decisions already made

| Decision       | Choice                                                                                      |
| -------------- | ------------------------------------------------------------------------------------------- |
| Route input    | GPX file                                                                                    |
| DTM handling   | GDAL, through `rasterio` and `pyproj` (pip wheels bundle GDAL, so no system install needed) |
| App build step | None. Native ES modules and the existing import map; `python3 -m http.server` keeps working |

## Out of scope

- Changing how the ride looks, or adding new scenery and weather.
- TypeScript, a bundler or a UI framework.
- Rewriting the Three.js rendering approach.

## Where things stand

- `index.html`: about 1,660 dense lines holding the whole app. No tests.
- Course data is JavaScript that sets `window.RIDE_COURSES`; terrain is base64 inside it.
- Values that only make sense for Leckhampton are fixed in code: `COURSE` only accepts `leckhampton`, `START = 850`, sheep above 175 m, hay stooks below 150 m, quarry smoke, and the ride log label.
- `tools/build_leckhampton.py` works for England only: Environment Agency WCS, hand-written British National Grid maths, a TIFF reader for uncompressed float32 only, and a route from waypoints sent to a public router.
- `tools/build_leckhampton_osm.py` reads another project's cache (`~/real-ride/osm-cache`), so it can't be reproduced.
- Scenery placement uses one shared seeded random stream, so the order of calls decides where every tree and sheep goes.
- `assets/textures.js` (21 MB) exists only so the page can be opened from `file://`.
- `deploy.sh` publishes to the original author's Spacefast space.

## Target layout

```
index.html                 markup, import map, <script type="module" src="src/main.js">
styles/main.css
src/
  main.js                  start-up: read options, load course, build scene, start the loop
  options.js               URL parameters in one place (?course, ?theme, ?scenery, ?hills, test options)
  util/random.js           seeded random streams, one per part of the scene
  util/noise.js            value noise, fbm, ridged noise
  render/                  renderer.js, sky.js, post.js (bloom, god rays, lens)
  course/                  loader.js, validate.js, road.js (curve, at(), nearRoad), terrain.js, valley.js (the invented course)
  scenery/                 grass.js, meadow.js, pines.js, buildings.js, pastoral.js (sheep, stooks), chalets.js, clouds.js, smoke.js
  weather.js
  cockpit.js
  physics.js               power to speed; no DOM and no Three.js, so it can be unit-tested
  devices/ftms.js          FTMS message encoding (no DOM; unit-tested)
  devices/trainer.js       Web Bluetooth connection and reconnects
  ui/                      hud.js, controls.js, ride-log.js, voice.js
  audio.js
courses/
  index.json               list of courses for the menu
  valley/course.json       the invented valley (procedural)
  leckhampton/             course.json, terrain.bin, road.json, scenery.json
assets/                    textures only
tools/coursebuilder/       Python package: build, validate, fetch helpers
tests/
  unit/                    node --test, for the pure JS modules
  visual/                  Playwright screenshot comparison
  python/                  pytest for the course builder
docs/                      course-format.md, adding-a-course.md, architecture.md
```

## Course format, version 1

A course is a folder under `courses/<id>/`. The app fetches files; there are no more globals.

`course.json`:

```json
{
  "format": 1,
  "id": "leckhampton",
  "name": "Leckhampton Hill loop",
  "description": "11.9 km loop over the Cotswold scarp above Cheltenham.",
  "kind": "survey",
  "loop": true,
  "start": 850,
  "origin": { "crs": "EPSG:27700", "x": 395640, "y": 218870 },
  "terrain": { "file": "terrain.bin", "size": 6200, "cells": 620, "min": 44.68, "max": 297.98 },
  "road": "road.json",
  "scenery": {
    "file": "scenery.json",
    "style": "pastoral-1800s",
    "options": { "sheepAbove": 175, "stooksBelow": 150, "smoke": [[-120.5, 640.2]] }
  },
  "credits": [
    { "text": "Heights: Environment Agency LiDAR Composite DTM", "licence": "OGL-UK-3.0", "url": "https://..." },
    {
      "text": "Route, buildings, woods and hedges © OpenStreetMap contributors",
      "licence": "ODbL-1.0",
      "url": "https://www.openstreetmap.org/copyright"
    }
  ]
}
```

- `terrain.bin`: little-endian uint16 heights, `(cells+1)²` values, row 0 at the north edge, scaled between `min` and `max`. The app reads it with `fetch().arrayBuffer()`, with no base64 step.
- `road.json`: `[[x, y, z], ...]` in local metres (x east, y up, z south), one point about every 15 m.
- `scenery.json`: buildings, single trees, hedge and wall pieces, and the woodland mask. Same contents as today's `_osm.js`. Optional.
- `credits` is required and must have at least one entry. The app shows it on screen, and the validator rejects a course without it.
- `kind: "procedural"` with `"generator": "valley"` describes the invented course, so the menu treats both kinds the same way.
- `courses/index.json` lists `id`, `name`, `lengthKm` and `climbM` for each course. The course builder keeps it up to date.
- `docs/course-format.md` is the specification, and `src/course/validate.js` and the Python validator both check against it.

Version 1 supports loops only, which is what the ride's position-wraps-around logic assumes. The builder rejects a route whose ends are more than 50 m apart unless given `--close`. Point-to-point routes are a later phase.

## Course builder

```
pip install -r tools/requirements.txt
python -m tools.coursebuilder build \
    --id my-loop --name "My Loop" \
    --route my-loop.gpx --dtm dtm/*.tif \
    [--scenery-style pastoral-1800s|plain] [--osm | --no-osm] [--margin 1300] [--close]
python -m tools.coursebuilder validate courses/my-loop
python -m tools.coursebuilder fetch-ea --route my-loop.gpx --out dtm/   # optional, England only
```

Steps:

1. **Read the GPX** (standard-library XML): track points, or route points if there's no track.
2. **Choose a working coordinate system**: the DTM's own one if it's projected in metres, otherwise the UTM zone for the route. Reproject with `pyproj`.
3. **Mosaic the DTM**: any GDAL-readable raster (GeoTIFF of any compression, ASC, IMG, VRT), in any coordinate system, reprojected on the fly with a rasterio `WarpedVRT`. Stop with a clear message if the DTM doesn't cover the route plus the margin; fill small no-data holes.
4. **Clean and resample the route**: remove out-and-back spurs, resample every 5 m.
5. **Road heights**: keep today's method (the flattest point across the road, median then moving-average smoothing). Report the steepest climb and descent and the total climbing.
6. **Terrain grid**: 10 m cells over the route's bounding square plus the margin, written as `terrain.bin`.
7. **Scenery**: fetch OpenStreetMap features from the Overpass API, cached in `tools/.cache/`, and convert them as `build_leckhampton_osm.py` does today. `--no-osm` skips this.
8. **Write** the course folder, update `courses/index.json`, and run the validator.

`build_leckhampton.py` and `build_leckhampton_osm.py` are removed once the new builder reproduces Leckhampton (see phase 4).

## Phases

Each phase is its own branch and pull request, and leaves the ride working.

### Phase 0: housekeeping

- `LICENSE`: keep the original copyright line and add one for this fork. Credit the original author in the README.
- Replace `deploy.sh` with a GitHub Pages workflow.
- Remove `assets/textures.js` and `file://` support. The README already tells people to run a local server, and fetching course files needs one anyway.
- Add a `package.json` for development tools only (ESLint and Prettier; Playwright joins in phase 1, where it is first used), plus `.editorconfig`, and `ruff` settings for Python. The app still has no build step.

### Phase 1: safety net

- Add test-only URL options: `?at=<metres>` to place the rider, `?freeze` to stop the clock, wind sway and weather changes, and `?weather=<name>`.
- Playwright takes screenshots in headless Chromium at fixed spots: the valley, valley Christmas, and Leckhampton (the climb, the vale, woods, buildings), each in two weathers.
- Done: rendering uses SwiftShader (software GPU), which gives identical pixels on every run, so comparisons are exact (zero tolerance). With `?freeze` the page also stops drawing once a view is complete, because software rendering takes several seconds per frame. See `tests/visual/README.md`.
- Cost: one view per course (three screenshots), about a minute in all. The first version had 18 views and took about 4.5 minutes, which was too slow for the value it added.
- **Policy: screenshot tests check the renderer, not the courses.** They stay a fixed set (the valley, Christmas, and Leckhampton as the one survey course) and do not grow when courses are added. Each contributed course is checked by the data validator instead (phases 3 and 4), which needs no browser and takes milliseconds per course.
- Commit the baseline screenshots. Later phases must match them unless a change is deliberate.

### Phase 2: split into modules

- Move code into the target layout without changing behaviour. Modules run in import order, so keeping the order keeps the shared random stream identical, and the screenshots should match pixel for pixel.
- Then, in a separate commit, give each part of the scene its own seeded stream. Scenery placement changes once, on purpose: retake the baseline and review it by eye. After that, editing one module no longer moves another module's trees.
- Unit tests for `physics.js`, `devices/ftms.js` and `options.js`.

### Phase 3: course format and loader

- A one-off conversion script turns today's `leckhampton.js` and `_osm.js` into `courses/leckhampton/` in format 1. No rebuild from source data is needed for this step.
- Move the values that only make sense for Leckhampton into `course.json`. The course button becomes a menu built from `courses/index.json`. `?course=<id>` accepts any listed course.
- Credits on screen come from `course.json`. The ride log shows the course name from the data (this also fixes the "Alps" label).
- Screenshots must match the phase 2 baseline.

### Phase 4: course builder

- Build `tools/coursebuilder/` as described above.
- pytest tests with small synthetic DTMs: a tilted plane gives a known gradient, a no-data hole gets filled, and another file uses a different coordinate system.
- **Acceptance test:** export the Leckhampton road as GPX (from British National Grid to WGS84 with pyproj), fetch Environment Agency tiles with `fetch-ea`, rebuild, and compare. Road heights within 0.5 m on average and total climbing within 3 %. OpenStreetMap features will differ slightly because the data is newer; that's expected.
- Remove the two old Leckhampton scripts.

### Phase 5: documentation and CI

- `docs/adding-a-course.md`: a step-by-step walkthrough with sources of free DTM data (Environment Agency, Scottish Remote Sensing Portal, USGS 3DEP, IGN RGE ALTI, swisstopo swissALTI3D and others), checking the result locally, and opening a pull request.
- `docs/course-format.md`, `docs/architecture.md`, `CONTRIBUTING.md`, and pull request and issue templates (including a "new course" checklist covering licence and credits).
- GitHub Actions on each pull request: ESLint and Prettier, `node --test`, ruff and pytest, and validating every course in `courses/` (data checks only, so the cost stays negligible however many courses there are).
- Visual tests run locally at first. GPU rendering in CI (SwiftShader) differs from desktop GPUs; they can join CI later with a tolerance tuned for SwiftShader.

### Later

- Point-to-point routes (stop or turn round at the end).
- Building a course from a local OpenStreetMap extract, without Overpass.
- Dropping the hand-written grid-reference maths from the app; nothing in the app needs it after phase 3.

## Risks

| Risk                                                         | Mitigation                                                                                                                          |
| ------------------------------------------------------------ | ----------------------------------------------------------------------------------------------------------------------------------- |
| Splitting 1,660 dense lines breaks something subtle          | Phase 1 screenshots; move code without changing it; pull requests small enough to review                                            |
| The one-time scenery reshuffle in phase 2 makes a view worse | Review the new baseline by eye; seeds can be tuned per stream                                                                       |
| GDAL install problems for contributors                       | rasterio wheels bundle GDAL for Linux, macOS and Windows; document a conda fallback                                                 |
| Contributed courses with unclear data licences               | `credits` required by the validator; licence checklist in the pull request template                                                 |
| Large course files bloat the repo                            | Binary terrain is about 0.75 MB for a 6 km square, a quarter smaller than today's base64. The validator warns above 5 MB per course |

## Open questions

1. Keep the GitHub fork link (lets you offer changes back to the original) or make this a standalone repository?
2. Host on GitHub Pages? The README's live link points to the original author's site.
3. Keep the "Starry" weather that only appears on localhost, or finish it or remove it?
4. Is a course contributed by pull request reviewed by you alone, or do you want a lighter process for courses than for code?
