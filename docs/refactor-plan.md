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
- Added in phase 3: optional `shortName`, `scenery.options.smoke` as a list of points, and `credits` may be empty for a procedural course. See "How phase 3 is done".
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

Status: done. One deviation from the target layout: `state.js` (the ride state, `window.ride`) and `scene.js` (the build order) were added; the ride state did not fit any of the planned modules.

- Move code into the target layout without changing behaviour. Modules run in import order, so keeping the order keeps the shared random stream identical, and the screenshots should match pixel for pixel.
- Then, in a separate commit, give each part of the scene its own seeded stream. Scenery placement changes once, on purpose: retake the baseline and review it by eye. After that, editing one module no longer moves another module's trees.
- Unit tests for `physics.js`, `devices/ftms.js` and `options.js`.

#### How phase 2 is done

Each step is its own commit, and every step except the last must keep the three screenshot baselines pixel-identical.

1. **Prepare inside `index.html`.** Small changes that make a clean split possible, without changing behaviour:
   - Shared shader uniforms (`uTime`, `uSunAmt`, the rain amount and others) move to the top, because sections use them before the section that declares them.
   - The smoothed gradient moves from a variable declared in the ride loop to `st.grade`, because the trainer code, earlier in the file, reads it.
   - The weather code no longer reassigns the sky's environment map directly; the sky section provides a function that swaps it.
   - URL parameters are read in one place (`options.js`).
   - The speed model (`physics.js`) and the FTMS trainer messages (`devices/ftms.js`) become pure functions with the same arithmetic in the same order.
2. **Split.** The script moves into `src/` modules. A one-off script slices the sections, then works out each module's imports and exports from what it declares and uses, and refuses to produce an import that points to a later module. Modules still build their part of the scene when imported, and `src/main.js` imports them in the original order, so the random stream is consumed in the same order. Turning modules into explicit `init()` functions is left for later; it is a bigger change than a move. The CSS moves to `styles/main.css`, and the Pages workflow publishes `src/` and `styles/`.
3. **Format and lint.** Prettier reformats `src/`, and ESLint now covers it. Lint fixes must not change behaviour.
4. **Unit tests** with Node's built-in test runner (`node --test`), no new dependencies.
5. **Separate random streams.** Each part of the scene gets its own seeded stream, and each patch of verge grass is seeded by its position on the road, so grass no longer depends on the order patches are built in. This changes the picture once: retake the baselines and review them by eye.

### Phase 3: course format and loader

Status: done. Deviations from the target layout: the loader stays in `course/course.js` rather than a new `loader.js`, the valley's road stays in `course/road.js` rather than `valley.js`, and `ui/panels.js` and `ui/course-menu.js` were added. Writing `docs/course-format.md` waits for phase 5; until then the format is described in this plan and enforced by `src/course/validate.js`.

- A one-off conversion script turns today's `leckhampton.js` and `_osm.js` into `courses/leckhampton/` in format 1. No rebuild from source data is needed for this step.
- Move the values that only make sense for Leckhampton into `course.json`. The course button becomes a menu built from `courses/index.json`. `?course=<id>` accepts any listed course.
- Credits on screen come from `course.json`. The ride log shows the course name from the data (this also fixes the "Alps" label).
- Screenshots must match the phase 2 baseline.

#### How phase 3 is done

- **Conversion.** `tools/convert_legacy_course.py` (standard library only) reads `assets/<id>.js` and `assets/<id>_osm.js` and writes `courses/<id>/`. `terrain.bin` is the existing uint16 heights, unchanged. Numbers are copied exactly, so the ride is identical. The old JavaScript course files are then deleted. The converter goes in phase 4 along with the two old build scripts, which still write the old format until then.
- **Format additions found while converting** (these become part of format 1):
  - `shortName` (optional): for the course button and the ride log ("Leckhampton"). If it's missing, `name` is used.
  - `scenery.json` holds `buildings`, `trees`, `lines` and `woods`. `woods` is a bitmask with one bit per terrain grid point, base64-encoded.
  - `scenery.options.smoke` is a list of `[x, z]` points. Smoke rises from the steepest ground within about 260 m of each point, which is how Leckhampton's quarry works today.
  - `credits` is required for `survey` courses. A `procedural` course may leave it empty, because there is no outside data to credit.
- **Loader** (`src/course/course.js`): reads `courses/index.json`, picks the course named by `?course=<id>` (anything not listed falls back to the valley), fetches `course.json`, checks it with `src/course/validate.js`, and then fetches the terrain, road and scenery. A broken course shows the reason in place of the loading message rather than a blank page.
- **What moves out of code:** the start position (`START = 850`), the sheep and stook heights, the quarry smoke, the credits, the ride log names, and the course button label. Scenery style `pastoral-1800s` turns on the sheep and stooks. The broadleaf trees and buildings go with any `survey` course.
- **Christmas** is a theme of the valley generator. `XMAS` moves from `options.js` to `course.js`, because only the loaded course can say whether the theme applies.
- **Course menu:** the Course button keeps its label and opens a panel styled like the ride log, listing every course with its length and climbing. Choosing one reloads the page with `?course=<id>`.
- **Ride log:** shows each ride's course by its `shortName` from `courses/index.json`. Rides on a course that's no longer listed show its id. Valley rides were labelled "Alps" by mistake; they now show "Valley".
- **Checks:**
  - The unit tests validate every folder in `courses/`: the fields, the terrain file size, and that the course is listed in `index.json`. This is data only, so the cost stays negligible however many courses are added.
  - `validate.js` itself has unit tests.
  - The three screenshots must match exactly.

### Phase 4: course builder

Status: done.

- **Acceptance test:** passes, with road heights 0.11 m apart on average (0.58 m at most) and climbing 228 m both before and after.
- **Scenery check:** a full build with OpenStreetMap, outside the test, matched the old buildings and hedges almost exactly (8,238 against 8,240 buildings; 906 against 907 hedge and wall pieces). It found more single trees and woodland near the edges of the terrain square, which the old cache didn't cover. In the ride, the rebuilt course looks almost identical to the current one.
- **Changes during the build:**
  - `build.py` holds the build steps, and `__main__.py` only reads the command line.
  - `fetch-ea` fetches two tiles at a time and retries timeouts, because the service sometimes takes more than a minute to answer.

- Build `tools/coursebuilder/` as described above.
- pytest tests with small synthetic DTMs: a tilted plane gives a known gradient, a no-data hole gets filled, and another file uses a different coordinate system.
- **Acceptance test:** export the Leckhampton road as GPX (from British National Grid to WGS84 with pyproj), fetch Environment Agency tiles with `fetch-ea`, rebuild, and compare. Road heights within 0.5 m on average and total climbing within 3 %. OpenStreetMap features will differ slightly because the data is newer; that's expected.
- Remove the two old Leckhampton scripts.

#### How phase 4 is done

- **Setup:** `tools/requirements.txt` (numpy, pyproj, rasterio) and `tools/requirements-dev.txt` (adds pytest and ruff). Development uses a `.venv` in the project folder, which git ignores.
- **Modules** in `tools/coursebuilder/`:

  | Module        | What it does                                                                                              |
  | ------------- | --------------------------------------------------------------------------------------------------------- |
  | `gpx.py`      | Reads the GPX file.                                                                                       |
  | `route.py`    | Removes spurs, resamples every 5 m, and checks or closes the loop.                                        |
  | `frame.py`    | Chooses the working coordinate system and the local frame.                                                |
  | `dtm.py`      | Opens the DTM files, samples the fine heights near the road, builds the terrain grid and fills its holes. |
  | `road.py`     | Road heights, smoothing and statistics.                                                                   |
  | `osm.py`      | Fetches OpenStreetMap features from Overpass (cached), converts them, and builds the woodland mask.       |
  | `course.py`   | Writes the course folder and updates `courses/index.json`.                                                |
  | `validate.py` | Checks a course against the format.                                                                       |
  | `ea.py`       | `fetch-ea`.                                                                                               |
  | `__main__.py` | The command line.                                                                                         |

- **Working coordinate system:** the first DTM's own system, if it is projected in metres and its scale error at the route is under 0.1 %. Otherwise the route's UTM zone. (Canada's national Lambert projection, for example, stretches distances by up to about 0.5 % in the south, which would make roads slightly too long.)
- **DTM sources:**
  - **Mixed files:** different resolutions and coordinate systems can be mixed. Each file is reprojected on the fly with `rasterio.warp.reproject`, finest last, so where files overlap the finest wins.
  - **Fine heights:** road heights come from 2 m tiles along the road, as now. The terrain is a 10 m grid, averaged over each cell.
- **Gaps in the DTM:**
  - **Small holes:** terrain grid points with no data are filled with GDAL's `fillnodata` from data up to 200 m away. Road points without fine heights (a gap, or water) take the filled terrain's height, and the builder says how many did.
  - **Stop with a clear message:** if more than 1 % of the terrain grid has no data, if a hole is too wide to fill, or if the DTM misses the road altogether. The message gives the missing area in latitude and longitude, and suggests a smaller `--margin` if the gap is at the edges.
- **Road heights:** today's method (the flattest point across the road, a 5-point median, then two passes of a 7-point moving average). The smoothing now wraps round the loop's ends.
- **Pastoral scenery:** with `--scenery-style pastoral-1800s`, sheep appear above the 65th percentile of the road's heights and stooks below the 35th, rounded to 5 m. `--sheep-above`, `--stooks-below` and `--smoke LAT,LON` (repeatable) override them.
- **Credits:**
  - **Heights credit:** `--heights-credit TEXT --heights-licence ID [--heights-url URL]` are required. `fetch-ea` prints the values to use for Environment Agency data.
  - **OpenStreetMap credit:** added automatically unless `--no-osm`.
  - **Extra sources:** `--credit "TEXT|LICENCE|URL"` (repeatable) adds one, such as wherever the GPX came from.
- **OpenStreetMap features:**
  - **Request:** one Overpass request for the terrain square: buildings, single trees, woods and forests, and hedges and walls.
  - **Cache:** responses are kept in `tools/.cache/overpass-<hash>.json`, so a rebuild doesn't fetch again.
  - **User-Agent:** a generic one naming the tool.
- **Two validators kept in step:** `tests/course-cases.json` lists courses that should pass or fail. Both the JavaScript and the Python unit tests run every case.
- **Acceptance test** (`tests/python/test_leckhampton.py`): runs only when `COURSEBUILDER_NETWORK=1` is set. It needs about 50 MB of Environment Agency tiles, kept in `tools/.cache/`. Heights are compared at the nearest rebuilt road point to each original one. The committed Leckhampton course is not replaced: its scenery would change with newer OpenStreetMap data, and the screenshot baseline with it. Rebuilding it is a separate choice.
- **Removed:** `build_leckhampton.py`, `build_leckhampton_osm.py` and `convert_legacy_course.py`.

### Phase 5: documentation and CI

- `docs/adding-a-course.md`: a step-by-step walkthrough with sources of free DTM data (Environment Agency, Scottish Remote Sensing Portal, USGS 3DEP, IGN RGE ALTI, swisstopo swissALTI3D and others), checking the result locally, and opening a pull request.
- `docs/course-format.md`, `docs/architecture.md`, `CONTRIBUTING.md`, and pull request and issue templates (including a "new course" checklist covering licence and credits).
- GitHub Actions on each pull request: ESLint and Prettier, `node --test`, ruff and pytest, and validating every course in `courses/` (data checks only, so the cost stays negligible however many courses there are).
- Visual tests run locally at first. GPU rendering in CI (SwiftShader) differs from desktop GPUs; they can join CI later with a tolerance tuned for SwiftShader.

#### How phase 5 is done

- **`docs/course-format.md`** becomes the specification. It covers every field, the local frame, what each scenery entry means, and what the validators check. The format section in this plan then points to it.
- **`docs/adding-a-course.md`**:
  - The steps: get a GPX, get a DTM, install the builder, build, ride it locally, tune it, and open a pull request.
  - A table of free DTM sources with their licences. The links were checked when writing.
  - A worked example for each of the two kinds of source: England with `fetch-ea`, and Canada's HRDEM, where the builder chooses UTM itself.
- **`docs/architecture.md`**: how start-up works, what each module does, random streams, how a course is loaded, the frame loop, the test hooks, and where the builder fits in.
- **`CONTRIBUTING.md`**: setup, the checks, code style, the screenshot test policy, and the licences of code and data.
- **Templates:**
  - Pull requests: a short template with a "new course" checklist (credits, licence, validator, ridden locally, size).
  - Issues: forms for a bug and for a course proposal.
- **CI (`.github/workflows/ci.yml`)**, on every pull request and on pushes to `main`:
  - A JavaScript job: `npm ci`, ESLint, Prettier, and `npm test`, which includes validating every course.
  - A Python job: Ruff, pytest, and `coursebuilder validate`.
  - The acceptance test and the screenshot tests stay local.
  - Playwright's browsers aren't downloaded, because nothing in CI uses them.
- **Found while writing:** the building drawing code is switched off for every course (`SHOW_TOWN = false`, chosen for Leckhampton's 19th-century look). So `buildings` only keeps trees off buildings for now. The docs say so, and turning it on per scenery style goes under "Later".

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
