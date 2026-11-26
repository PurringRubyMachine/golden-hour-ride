# Golden Hour Ride

An indoor cycling ride that runs in the browser (Three.js). Ride an invented mountain valley, or real roads in England and Canada built from LiDAR survey data.

Live: https://purringrubymachine.github.io/golden-hour-ride/ · Leckhampton loop: https://purringrubymachine.github.io/golden-hour-ride/?course=leckhampton · Gatineau Park Loop: https://purringrubymachine.github.io/golden-hour-ride/?course=gatineau-park-loop

This project is a fork of [jamiemarsland/golden-hour-ride](https://github.com/jamiemarsland/golden-hour-ride) by Jamie Marsland, who wrote the original ride. The fork has been refactored so it is easier to maintain, and so anyone with a LiDAR terrain model can add their own course: see [docs/adding-a-course.md](docs/adding-a-course.md).

## Changes from the original

This fork started from the original's commit of 22 November 2026 ("Add MIT licence and licence notes"). Since then:

**Structure**

- The single `index.html` is split into ES modules under `src/`, one per part of the ride, still with no build step ([#3](https://github.com/PurringRubyMachine/golden-hour-ride/pull/3)).
- Courses are data, not code: each is a folder under `courses/` in a documented, validated format, listed in a course menu, so adding one needs no code ([#4](https://github.com/PurringRubyMachine/golden-hour-ride/pull/4)).
- Hosted on GitHub Pages; the Spacefast deploy script and the embedded copy of the textures for opening from disk are gone ([#1](https://github.com/PurringRubyMachine/golden-hour-ride/pull/1)).

**Courses**

- A course builder (`tools/coursebuilder/`, Python): a GPX route and LiDAR DTM files of any format and coordinate system in, a course folder out, with buildings, woods, trees, hedges and walls from OpenStreetMap ([#5](https://github.com/PurringRubyMachine/golden-hour-ride/pull/5)).
  - `fetch-ea` downloads Environment Agency LiDAR for a route in England ([#5](https://github.com/PurringRubyMachine/golden-hour-ride/pull/5)); `fetch-hrdem` reads Natural Resources Canada's HRDEM for a route in Canada ([#13](https://github.com/PurringRubyMachine/golden-hour-ride/pull/13)).
  - Roads are drawn straight across bridges, where a bare-ground DTM would dip into the valley beneath ([#13](https://github.com/PurringRubyMachine/golden-hour-ride/pull/13)).
  - Each course records how it was built (`build.json`: the command, the route's checksum, the DTM files, the map data's date) ([#11](https://github.com/PurringRubyMachine/golden-hour-ride/pull/11)).
- Leckhampton is rebuilt with the builder, so it can be built again from its sources (now 11.8 km) ([#10](https://github.com/PurringRubyMachine/golden-hour-ride/pull/10), [#11](https://github.com/PurringRubyMachine/golden-hour-ride/pull/11)).
- A new course: the **Gatineau Park Loop**, 41 km in Quebec, up to the Champlain Lookout ([#13](https://github.com/PurringRubyMachine/golden-hour-ride/pull/13)).

**Riding**

- **Quality levels**: Auto, Low, Medium and High. On a laptop's built-in Intel graphics the ride went from 8–10 frames a second, with freezes of up to a second, to a steady 60 on Low ([#8](https://github.com/PurringRubyMachine/golden-hour-ride/pull/8), [#9](https://github.com/PurringRubyMachine/golden-hour-ride/pull/9), [#15](https://github.com/PurringRubyMachine/golden-hour-ride/pull/15)).
- **Large forested courses**: woods dense along the road and thinning into the distance, distant woodland drawn as canopy, and distant ground and trees in less detail ([#14](https://github.com/PurringRubyMachine/golden-hour-ride/pull/14), [#15](https://github.com/PurringRubyMachine/golden-hour-ride/pull/15)).
- **A course map**: the loop from above with you on it as a red dot, the height profile, and where you are on the loop ([#16](https://github.com/PurringRubyMachine/golden-hour-ride/pull/16)).
- The trainer button explains why Bluetooth is missing (it is switched off by default in Chrome on Linux) instead of asking for Chrome ([#7](https://github.com/PurringRubyMachine/golden-hour-ride/pull/7)).
- The unfinished Starry weather is removed ([#12](https://github.com/PurringRubyMachine/golden-hour-ride/pull/12)).

**For contributors**

- Tests: unit tests, the course builder's tests, data checks on every course, and three screenshot tests ([#2](https://github.com/PurringRubyMachine/golden-hour-ride/pull/2), [#3](https://github.com/PurringRubyMachine/golden-hour-ride/pull/3), [#4](https://github.com/PurringRubyMachine/golden-hour-ride/pull/4), [#5](https://github.com/PurringRubyMachine/golden-hour-ride/pull/5)).
- Checks on every pull request, documentation (architecture, the course format, adding a course, contributing) and pull request and issue templates ([#6](https://github.com/PurringRubyMachine/golden-hour-ride/pull/6)).
- Frame-rate measurement on the real graphics chip (`tests/perf/`) ([#8](https://github.com/PurringRubyMachine/golden-hour-ride/pull/8)).

**Not in this fork.** The original has carried on separately since the fork, adding handlebar controllers (Zwift Ride, OpenBikeControl), twelve virtual gears, a Stop ride summary with a ride file for Strava, redesigned controls, and seasons (Summer, Christmas, the Alps in snow). Those aren't here.

## What's in it

- Three courses: an invented mountain valley; a real 11.8 km Leckhampton loop built from Environment Agency lidar, dressed as the 19th-century hill (sheep, hay stooks, quarry smoke); and the 41 km Gatineau Park Loop in Quebec, built from Natural Resources Canada's HRDEM.
- Four looks: Golden, Overcast, Rain and Mist. Buttons at the top, keys 1–4, or by voice.
- Skip forward and back 250 m with the arrow keys.
- A course map in the corner: the loop from above with you on it, the height profile, and where you are on the loop ("17.4 of 41.1 km", from the course's beginning). The Map button or the M key turns it off and on; the choice is kept in the browser.
- Hide everything on screen for a clean view: the Hide info button, the H key, or say "hide". Press H, click, or say "show" to bring it back.
- Power from a slider, or from a Bluetooth trainer (Chrome or Edge; on Linux, first turn on _Experimental Web Platform features_ at `chrome://flags` — the trainer button explains if Bluetooth is missing). If the trainer supports resistance control (FTMS), the ride also sends it the road gradient, so climbs feel harder; the button shows "Trainer: power and gradient" or "Trainer: power only". The trainer feels half the road gradient by default; the − and + buttons beside the trainer button change that in steps of 10 %, from off to the full gradient, and the choice is kept in the browser (`?hills=` sets it for one visit). With voice on, say "easier" or "harder" to move it by 20 %, "flat" for off, or "full" for all of it. The last trainer is remembered: the button reads "Reconnect trainer" and rejoins it without the browser's device list where Chrome allows that, and a dropped connection is retried automatically.
- Quality: Auto, Low, Medium or High (the Quality button, kept in the browser; `?quality=` for one visit). Auto starts at Medium on built-in graphics and High otherwise, and steps down if the ride isn't smooth; it remembers where it settled. Low runs at 60 fps on a laptop's built-in Intel graphics.
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

For a route in England, `fetch-ea --route my-loop.gpx --out dtm/` downloads Environment Agency LiDAR for it, and for one in Canada `fetch-hrdem` reads Natural Resources Canada's HRDEM; both print the credit options to use. `build --help` lists the rest: pastoral scenery, smoke, the start point, and turning off OpenStreetMap features. The full walkthrough, with free DTM sources for many countries, is [docs/adding-a-course.md](docs/adding-a-course.md).

## Layout

- `index.html` – the page: controls, display and the import map for Three.js.
- `src/` – the ride, as ES modules. `main.js` loads the textures and course, then `scene.js` builds the scene, one module per part:
  - `course/` – loading and checking a course, the road line and the ground
  - `scenery/` – road surface, grass, trees, buildings, clouds and the rest
  - `render/` – renderer, textures, sky and post-processing
  - `devices/` – smart trainers (FTMS)
  - `ui/` – controls, course menu and map, ride log and voice
  - `physics.js` – the speed model; `weather.js`; `ride.js` – the frame loop
- `styles/` – the page's CSS.
- `courses/` – one folder per course; `index.json` lists them for the menu. The format is described in [docs/course-format.md](docs/course-format.md).
- `assets/` – textures.
- `tests/` – unit tests (`unit/`), screenshot tests (`visual/`) and frame-rate measurements (`perf/`).
- `tools/coursebuilder/` – the course builder: a GPX route and LiDAR DTM files in, a course folder out (see below).
- `docs/` – [architecture](docs/architecture.md), [course format](docs/course-format.md), [adding a course](docs/adding-a-course.md), the [refactor plan](docs/refactor-plan.md) and the [performance plan](docs/performance-plan.md).

Contributions are welcome: see [CONTRIBUTING.md](CONTRIBUTING.md).

## Credits

- Original ride: Jamie Marsland.
- Textures: Poly Haven (CC0).
- Terrain: Environment Agency LiDAR Composite DTM, Open Government Licence v3.0; Natural Resources Canada HRDEM, Open Government Licence – Canada.
- Gatineau Park Loop route: [Ride with GPS route 34405323](https://ridewithgps.com/routes/34405323).
- Roads, woodland and field boundaries: © OpenStreetMap contributors, ODbL.
- 3D engine: Three.js (MIT), loaded from jsDelivr.

## Licence

The code is released under the MIT licence: see `LICENSE`. Use it, change it, build your own ride.

The MIT licence covers the code only. The course data in `courses/` is derived from the sources credited above and stays under their terms, recorded in each course's `credits` (and its README): the Open Government Licence v3.0 or the Open Government Licence – Canada for the terrain, and the ODbL for the OpenStreetMap data. If you share or adapt that data, keep those credits.
