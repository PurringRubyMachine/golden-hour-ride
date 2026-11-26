# Architecture

Golden Hour Ride is a static web page: HTML, CSS and JavaScript modules that the browser loads as they are. There is no build step and no server code. Three.js comes from jsDelivr through the import map in `index.html`. Everything else in the repository supports the page: course data, the Python course builder, tests and docs.

```
index.html, styles/     the page: controls, display, import map
src/                    the ride, as ES modules
courses/                one folder per course, plus index.json
assets/                 textures (Poly Haven, CC0)
tools/coursebuilder/    Python: GPX + DTM -> course folder
tests/                  unit/ (node --test), python/ (pytest), visual/ (Playwright)
docs/                   this, the course format, adding a course, the refactor plan
```

## Start-up

`src/main.js` runs in two stages:

1. **Load.** It imports `render/textures.js` and `course/course.js`, which wait on files: the texture images, and the course (`courses/index.json`, the chosen `course.json`, then its terrain, road and scenery). A module that waits at the top level lets its siblings run meanwhile, so both download together.
2. **Build.** Only once both have finished does it `await import('./scene.js')`. `scene.js` imports every other module in order, and each one builds its part of the scene as it is imported: the renderer and sky, the road line and ground, then the scenery, weather, cockpit, post-processing, physics, controls, devices and finally `ride.js`, which starts the frame loop. So every scene module can rely on the textures and the course being ready.

If a course is broken, `course.js` puts the reason in place of the loading message and stops.

## Modules

| Module               | What it does                                                                                                                                       |
| -------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------- |
| `options.js`         | Reads the address bar once: `?course`, `?theme`, `?scenery`, `?hills`, and the test options.                                                       |
| `course/course.js`   | Loads and validates the course; exports `course` (its course.json), `courses` (the index), `real` (survey data, or `null` for the valley), `XMAS`. |
| `course/validate.js` | The format checks (no DOM, so the unit tests use it too).                                                                                          |
| `course/road.js`     | The road as a smooth closed curve: `at(s)` gives position and direction `s` metres along; `nearRoad(x, z)` how far a point is from it.             |
| `course/terrain.js`  | The ground mesh: surveyed heights, or the valley's noise mountains; blended into the road's own heights beside it.                                 |
| `scenery/*`          | Road surface, verge grass (built in patches near the rider), meadow, trees, hedges and walls, sheep and stooks, chalets and lights, clouds, smoke. |
| `render/*`           | Renderer and camera, textures, sky and sun, post-processing (bloom, light shafts, lens), and the quality levels.                                   |
| `weather.js`         | The weathers and the change from one to another.                                                                                                   |
| `physics.js`         | Speed from power and gradient. Pure: no DOM, no Three.js, unit-tested.                                                                             |
| `devices/ftms.js`    | Smart trainer messages (Bluetooth FTMS). Pure, unit-tested.                                                                                        |
| `devices/trainer.js` | The Bluetooth connection: power in, gradient out, reconnects.                                                                                      |
| `ui/*`               | Keys and buttons, the course menu and map, the ride log, voice commands, and the drop-down panels.                                                 |
| `state.js`           | The ride's state (`st`), shared by the controls, the loop and the tests as `window.ride`.                                                          |
| `ride.js`            | The frame loop: speed, camera, nearby grass, drawing.                                                                                              |

## Courses

The app treats both kinds of course the same way through `course.json`: a `procedural` course (the valley) is generated in code, and a `survey` course is read from files. What differs between courses lives in data, not code: the start point, credits, names, scenery style and its options. See [course-format.md](course-format.md).

`real` is the survey course's data: `size`, `cells` and `h` (heights), `road`, `buildings`, `trees`, `lines`, and `wood(x, z)`. Modules check `real` to choose between surveyed and generated ground, and `course.scenery.style` for how to dress it.

Trees go where `wood(x, z)` says there is woodland, at most 26,000 of them. Where there is little woodland they cover it evenly; where there is a lot (more than about 9 km², as in Gatineau Park), they are planted near the road instead, thinning with distance. Beyond about 150 m, wooded ground is drawn in a canopy colour, so distant forest reads as forest. A course with a photo of the ground from above (`ground.jpg`, see the course format) has its ground coloured from the photo instead beyond 60–80 m, with a light tint of it nearer; the photo loads after the ride starts and fades in.

## Random numbers

Placement is random but the same on every visit: each module draws from its own seeded stream (`makeRandom('trees')` in `util/random.js`). Streams are independent, so changing how many random numbers one module uses doesn't move another module's trees. A new module should take its own stream with a new name.

## Quality and performance

Most riders have a laptop's built-in graphics, which are limited mainly by how many pixels they shade, then by shadows and post-processing, then by geometry ([performance-plan.md](performance-plan.md) has the measurements). So:

- **Quality levels.** `render/quality-levels.js` defines Low, Medium and High (render scale, shadows, bloom and light shafts, anti-aliasing, meadow density, verge grass and tree trunk distances) and the automatic choice; it is pure and unit-tested. `render/quality.js` holds the rider's choice and applies a level: a module that depends on the level registers with `onQuality(fn)`, which calls it now and on every change, so every setting can change mid-ride without a reload. Auto starts from the graphics chip's name, steps down when more than a quarter of the last 3 seconds went on frames over 20 ms, never steps up, and remembers where it settled. The screenshot tests (`?freeze`) use High.
- **Tiles.** Trees (250 m tiles, larger on large courses) and the ground (8 × 8 tiles, at most 100 cells across) are drawn in pieces the camera, and the sun's shadow pass, can each skip. A new kind of scenery spread over the course should be tiled too, not one mesh with `frustumCulled = false`.
- **Distance.** Each ground tile comes at three levels of detail (`course/terrain-lod.js`: every grid point, every second or every fourth, with whole edges so tiles meet without cracks), chosen each frame by distance. At lower quality, distant tree tiles and trunks are not drawn (the woods carry on as the ground's canopy colour), and fewer trees and verge tufts are drawn.
- **Budget.** Keep Low under about 1.5 million triangles a frame (`window.ride.stats` gives the count; `tests/perf/measure.js` measures it on the real graphics chip).

## The frame loop

Each frame, `ride.js`:

- turns the power (slider, keys or trainer) and the road's gradient into speed (`physics.js`), and moves the rider along the road;
- updates the smoothed gradient (`st.grade`), which `devices/trainer.js` sends to a smart trainer four times a second, scaled by the Hills setting;
- builds the next verge grass patch near the rider (one per frame, so the ride stays smooth) and drops patches left behind;
- shows the trees and trunks near the camera and picks each ground tile's level of detail (`nearTrees`, `terrainDetail`), and lets Auto quality judge the frame;
- moves the camera, sun and weather, and draws through the post-processing chain.

## Test hooks

`window.ride` exposes the ride state for tests and for looking around by hand (`ride.stats`: draw calls, triangles and the quality level of the last frame): `ride.go(metres)` jumps along the road, `ride.weather(name, true)` changes the weather at once, `ride.held` says a frozen view is complete. `?freeze` stops the clock and holds the picture still; `?at=` and `?weather=` set the start. See [tests/visual/README.md](../tests/visual/README.md).

## Course builder

`tools/coursebuilder/` is a Python package, run as `python -m tools.coursebuilder`. It shares nothing with the app but the course format, and its validator mirrors `validate.js` (the shared cases in `tests/course-cases.json` keep them agreeing).

| Module        | What it does                                                                                                    |
| ------------- | --------------------------------------------------------------------------------------------------------------- |
| `gpx.py`      | Reads a GPX track or route.                                                                                     |
| `route.py`    | Removes spurs, resamples every 5 m, closes the loop.                                                            |
| `frame.py`    | Chooses the working coordinate system and the terrain square.                                                   |
| `dtm.py`      | Reads DTM files of any format and coordinate system; fine heights by the road; the terrain grid; filling holes. |
| `road.py`     | Road surface heights, straight across bridges, smoothing and statistics.                                        |
| `osm.py`      | OpenStreetMap features from Overpass, cached: scenery, the woodland mask, and road bridges.                     |
| `course.py`   | Writes the course folder and the index.                                                                         |
| `validate.py` | The format checks.                                                                                              |
| `ea.py`       | `fetch-ea`: Environment Agency LiDAR tiles for England.                                                         |
| `hrdem.py`    | `fetch-hrdem`: Natural Resources Canada's HRDEM, read in pieces from its cloud-optimised mosaics.               |
| `build.py`    | The build, step by step; `__main__.py` is the command line.                                                     |

## Tests

| Suite                 | Runs                                                                                             | Where          |
| --------------------- | ------------------------------------------------------------------------------------------------ | -------------- |
| `tests/unit/`         | `npm test`: physics, FTMS, options, random streams, the validator, every course's data           | CI and locally |
| `tests/python/`       | `pytest`: the builder against synthetic DTMs whose answers are known; the shared validator cases | CI and locally |
| `tests/visual/`       | `npm run test:visual`: three screenshots compared pixel for pixel                                | locally        |
| `tests/perf/`         | `node tests/perf/measure.js`: frame rate and draw counts on the real graphics chip               | locally        |
| `test_leckhampton.py` | Rebuilds Leckhampton from Environment Agency LiDAR and compares; needs `COURSEBUILDER_NETWORK=1` | locally        |

The screenshot set stays at three (the valley, Christmas, Leckhampton): it checks the renderer, not the courses. New courses are covered by the data checks, which cost almost nothing however many there are.
