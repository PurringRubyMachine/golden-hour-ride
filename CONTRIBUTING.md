# Contributing

Thank you for helping. New courses are especially welcome: see [docs/adding-a-course.md](docs/adding-a-course.md). For how the code fits together, see [docs/architecture.md](docs/architecture.md).

## Setup

```bash
npm install                                   # ESLint, Prettier, Playwright (no build step: these are tools only)
npm start                                     # serves the ride at http://localhost:8791/

python3 -m venv .venv                         # only for the course builder
.venv/bin/pip install -r tools/requirements-dev.txt
```

The ride needs a web server: browsers won't load the modules and textures from `file://`.

## Checks

Pull requests run these automatically (`.github/workflows/ci.yml`); run them before pushing:

```bash
npm run lint && npm run format:check && npm test
.venv/bin/ruff check . && .venv/bin/ruff format --check . && .venv/bin/pytest
```

Three more run only on your machine:

- **Screenshot tests** (`npm run test:visual`, about a minute, after `npx playwright install chromium` once). Run them for any change to the ride's code. They compare three views pixel for pixel; a change that is meant to alter the picture updates the baselines (`npm run test:visual:update`) in the same pull request, and says why. See [tests/visual/README.md](tests/visual/README.md).
- **Frame-rate measurements** (`node tests/perf/measure.js`, a minute or two). Run them for changes to scenery or rendering, on built-in graphics if you can, at each quality level you touch (`--query quality=low`), and give the numbers before and after in the pull request. See [tests/perf/README.md](tests/perf/README.md).
- **The Leckhampton acceptance test** (`COURSEBUILDER_NETWORK=1 .venv/bin/pytest tests/python/test_leckhampton.py`). Run it for changes to how the builder computes heights. It downloads about 50 MB of LiDAR the first time.

## Code

- JavaScript: ES modules in `src/`, formatted by Prettier (120 columns, single quotes), checked by ESLint. Keep pure logic (no DOM, no Three.js) in modules of its own so it can be unit-tested, as `physics.js` and `devices/ftms.js` are.
- Python: formatted and checked by Ruff (120 columns), Python 3.10 or later. The builder's errors for users are `BuildError`, with a message that says what to do.
- A module that places things at random takes its own stream: `makeRandom('name')`.
- Comments say why, not what. Docs and messages are plain English.
- If you change the course format, change [docs/course-format.md](docs/course-format.md), both validators and `tests/course-cases.json` together.

## Pull requests

- One change per pull request, small enough to review; describe what and why, and how you tested it.
- For a new course, the template's checklist covers what reviewers will look for.
- Bigger changes: open an issue first to talk it over.

## Licences

The code is MIT (see `LICENSE`). Course data stays under the licence of its sources, recorded in each course's `credits` and shown on screen. Only add data you're allowed to share and publish, with its credits.
