# Plan: record where each course comes from

## The problem

A course's credits say which sources it uses (on screen, from `course.json`), but nothing in the repository says exactly which files went in or how to build it again. For Leckhampton:

- the DTM tiles (60 Environment Agency GeoTIFFs) are only in `tools/.cache/`, which git ignores;
- the GPX is only in `tools/.cache/` too, and one sentence in the refactor plan says where it came from;
- the build command is in the refactor plan, not with the course.

## The fix

1. **The builder writes `build.json`** into every course folder, automatically, so it can't go out of date:

   ```json
   {
     "builtWith": "tools/coursebuilder",
     "date": "2026-11-26",
     "command": "python -m tools.coursebuilder build --id leckhampton ...",
     "route": { "file": "route.gpx", "sha256": "…", "kept": true },
     "dtm": { "workingCrs": "EPSG:27700", "files": ["ea_10m_392000_215000.tif", "…"] },
     "openStreetMap": { "dataAsOf": "2026-11-26T03:50:51Z" }
   }
   ```

   - `command` is the build as a command line, made from the options (not copied from the shell), so it's the same however the build was run.
   - Paths are written relative to the folder the builder ran in, or as bare file names if they're outside it, so a home folder (and the user name in it) never ends up in a published file.
   - `route.sha256` identifies the GPX without publishing it. `kept` says whether it was copied into the course (below).
   - `openStreetMap.dataAsOf` is Overpass's own timestamp for the data (`osm3s.timestamp_osm_base`); absent with `--no-osm`.
   - The app never reads it. It is not part of the course format's checks, so format 1 doesn't change; `docs/course-format.md` lists it under other files.

2. **`--keep-route`** copies the GPX into the course folder as `route.gpx`, and the recorded command then uses that copy, so anyone can rebuild the course from the repository. It is off by default: a GPX of your own ride shows where you ride. `docs/adding-a-course.md` says when to use it. Leckhampton is rebuilt with it (a public road loop drawn over OpenStreetMap).

3. **`courses/leckhampton/README.md`**: where each part comes from (route, heights, scenery), with their licences, and how to rebuild it (`fetch-ea` from the committed `route.gpx`, then the command in `build.json`). The command leaves the refactor plan, which points here instead.

## Checking

- Python tests: `build.json` is written with the right contents; paths outside the working folder become bare names; `--keep-route` copies the GPX and the command uses the copy; without it, no GPX is copied.
- Rebuild Leckhampton with `--keep-route`: `course.json`, `road.json`, `terrain.bin` and `scenery.json` come out byte for byte the same; only `build.json` and `route.gpx` are new.
- `validate`, `npm test`, screenshots unchanged.
