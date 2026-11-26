# Golden Hour Ride: notes for Claude Code

A browser cycling ride (Three.js, ES modules, no build step) with courses built from real terrain data by a Python course builder. Read `docs/architecture.md` for how it fits together and `CONTRIBUTING.md` for the checks and code style.

## Adding a course

People often ask for a new course by giving a route (a GPX file, or a link to one) and a terrain source (a link, or downloaded files). Follow [docs/adding-a-course.md](docs/adding-a-course.md); in short:

1. **Set up** if needed: `python3 -m venv .venv && .venv/bin/pip install -r tools/requirements-dev.txt`, and `npm install`.
2. **The route.** Save it under `tools/.cache/` (git ignores it). It must be a **track**, not a list of turns: on Ride with GPS, "GPX Track", not "GPX Route"; the builder warns when points are far apart. A download that needs signing in is the user's to do: ask them for the file. It must be a loop (ends within 50 m, or `--close` for a short gap on the same road).
3. **The heights.** A **DTM** (bare ground), never a DSM. In England use `fetch-ea`; in Canada, `fetch-hrdem`. Elsewhere, find the national source in the table in `docs/adding-a-course.md` and ask the user to download the tiles covering the route plus about 1.3 km round it, if you can't fetch them. Check the licence allows sharing the derived heights.
4. **The photo from above.** `fetch-sentinel2 --route … --out tools/.cache/s2-<id> --margin <the same as the build>` reads the clearest summer Sentinel-2 scene, anywhere. Look at the file before building with it (cloud, haze, harvested fields) and try another month (`--months 5-5`) if one suits the place better. A government aerial photo will do instead if its licence allows sharing (see `docs/adding-a-course.md`).
5. **Build** with `python -m tools.coursebuilder build` (see `build --help`). Give `--heights-credit`, `--heights-licence` and `--heights-url`, `--credit` for the route's source (a route drawn on a planner is over OpenStreetMap: ODbL), and `--imagery` with the credit options `fetch-sentinel2` prints. For a loop over about 25 km, use a smaller `--margin` (800) to keep the course under 5 MB (plus the photo, at most 2.5 MB).
6. **Read the report.** Climbing and steepest gradients should be believable for the road: a 20 %+ ramp on a road that has none usually means a bridge missing from OpenStreetMap, or a DSM.
7. **Choose a start** (`--start`, metres from the route's first point) with a view, not a car park; rebuild.
8. **Check**: `python -m tools.coursebuilder validate`, `npm test`, and look at the course in the ride (`npm start`, then `http://localhost:8791/?course=<id>`), at a few points (`&at=<metres>`).
9. **Write `courses/<id>/README.md`**: the sources with their licences and links, and how to rebuild (see `courses/gatineau-park-loop/README.md`). Commit the course folder (with the `build.json` the builder writes) and `courses/index.json`.

Rules:

- **Credit every source** in the course's credits: heights, route, the photo from above, OpenStreetMap (the builder adds that one). Only use data whose licence allows publishing it.
- **Don't commit someone else's GPX.** Use `--keep-route` only for a route the user made and is happy to publish. Never commit DTM files, or the downloaded photos (only the `ground.jpg` the builder writes).
- **Privacy**: a route that starts at someone's home shouldn't be published; suggest starting elsewhere on the loop.
- Don't add a screenshot test for a new course: the set stays at three; the data checks cover courses.

## Pull requests

- Contributors work on a fork and open pull requests against **PurringRubyMachine/golden-hour-ride**, not the original (jamiemarsland/golden-hour-ride), which has gone its own way.
- One change per pull request, on a branch; describe what, why and how it was checked. The template's checklist covers new courses.
- Run the checks in `CONTRIBUTING.md` first. For changes to the ride's code also run `npm run test:visual`; for scenery or rendering, `node tests/perf/measure.js`.
