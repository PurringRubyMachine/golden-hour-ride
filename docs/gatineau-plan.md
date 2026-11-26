# Plan: the Gatineau Park Loop course

A new course from a route on Ride with GPS and Natural Resources Canada's HRDEM terrain model: the first course outside England, and the first that needs the builder to fetch Canadian data.

## The route

[Ride with GPS route 34405323](https://ridewithgps.com/routes/34405323), "Gatineau Park Loop": 41.7 km, about 630 m of climbing. From parking P3 (Gamelin), up the Gatineau and Champlain Parkways to the Champlain Lookout, back by the Fortune and Gatineau Parkways. It is a loop (the ends are 2 m apart), 11.8 km east–west and 9.6 km north–south.

- **Getting it.** Ride with GPS gives the GPX file only to signed-in users. The route's public JSON (`/routes/34405323.json`) has the same track points; a small conversion keeps only latitude and longitude and writes a GPX. Done by hand for this course, not part of the builder: other routes will come as GPX from wherever riders plan them.
- **Credit and licence.** The route is another rider's plan, along public parkways mapped in OpenStreetMap. The course credits it as "Route: Gatineau Park Loop on Ride with GPS (route 34405323), along roads © OpenStreetMap contributors", under ODbL 1.0, with the route's link.
- **Not kept in the course** (`--keep-route` off): the GPX is the route's author's work, and republishing it is theirs to decide. `build.json` records its checksum, and the course README says how to get it again.

## The heights: `fetch-hrdem`

HRDEM comes as province-sized cloud-optimised GeoTIFF mosaics (1 m, in Canada Atlas Lambert, EPSG:3979), listed in a STAC catalogue. This loop crosses the line between two of them (`8_2` and `9_2`). Cloud-optimised files can be read in pieces over HTTP, so nothing large is downloaded:

- `python -m tools.coursebuilder fetch-hrdem --route loop.gpx --out tools/.cache/hrdem-loop`, like `fetch-ea`: 2 m tiles within 25 m of the road, 10 m tiles over the terrain square, 1 km each, in EPSG:3979's grid. Tiles already in the folder are not fetched again.
- It asks the STAC catalogue which DTM mosaics cover the square, then reads each tile's window from each mosaic that overlaps it (using the mosaic's overviews for the 10 m tiles), keeping valid pixels, and writes a small GeoTIFF.
- It prints the credit options to pass to `build`, as `fetch-ea` does.
- Tests, without the network: which tiles a route needs, and joining two mosaics at a seam (two small local GeoTIFFs standing in for them). A network test, like Leckhampton's, is not needed for this: the course build itself is the check.

The builder already works in UTM when the DTM's own system stretches distances (Canada Atlas Lambert does, by about half a percent here), so nothing else changes.

## Size, and how the app copes

A 41.7 km loop is the largest course yet. With the usual 1300 m margin the terrain square would be 14.4 km: 2.1 million height points, 4.2 MB, before scenery, where the guide asks for under 5 MB, and 4 million triangles of ground where Low's budget is 1.5 million in all.

1. **Build it first with a smaller margin** (800 m: 13.4 km, 3.6 MB), and measure: course size; frame rate at Low and High on the Intel chip (`tests/perf/measure.js`, with Gatineau added); how the woods look.
2. **Then decide**, from the numbers, whether the app needs changes for courses this large. Likely candidates, each its own pull request if needed:
   - **Trees**: a surveyed course gets at most 26,000 trees, spread over the woodland of the whole square; a forested park five times Leckhampton's area would look thin. Keeping trees nearer the road denser would fix it without drawing more.
   - **Ground**: distant terrain tiles at a coarser grid.

   This plan doesn't make those changes; it finds out whether they're needed.

## The course

- `courses/gatineau-park-loop/`: id `gatineau-park-loop`, name "Gatineau Park Loop", short name "Gatineau".
- Plain scenery (no sheep or hay stooks), trees and woods from OpenStreetMap.
- Start: choose a point with a view after riding it (the route begins in a car park).
- `courses/gatineau-park-loop/README.md`: sources, licences, and how to rebuild.
- Credits: the route (above); "Heights: Natural Resources Canada HRDEM, Open Government Licence – Canada" (`OGL-Canada-2.0`); OpenStreetMap for the scenery (the builder adds it).
- `docs/adding-a-course.md`: the Canada example uses `fetch-hrdem`.

## What happened

- **Route:** the GPX export needs signing in; the public JSON gave the same 1,855 track points. (A "GPX Route" export has only the 14 turns: the builder now warns when a GPX's points are far apart.)
- **Heights:** `fetch-hrdem` read 378 tiles (36 fine, 342 coarse; 40 MB) from mosaics `8_2` and `9_2` in about 8 seconds, with no gaps.
- **Builder speed:** the first build took over 10 minutes: for each of hundreds of fine tiles, the DTM reader converted all 378 files' bounds into the working coordinate system again. They are now worked out once per file: the build takes 71 seconds.
- **Bridges:** the first build had 20 % ramps where the road crosses two valleys on bridges (each passed twice): the bare-ground DTM has no bridge decks, so the road dipped 3–4 m. The builder now fetches road bridges from OpenStreetMap and draws the road straight across them (`road.across_bridges`): steepest 8.5 % up and 7.9 % down, climbing 668 m (Ride with GPS says 630). Leckhampton has three bridges too: its road is rebuilt, moving 14 of 791 points by up to 1.7 m, far from the start, and its climbing goes from 228 to 226 m. Its screenshot changes in the fields only: pastures and stubble are placed by road height, so their random draws shift.
- **The course:** 41.0 km, a 13.4 km terrain square (800 m margin), 3.9 MB. Start at 3 km, on the parkway (the route begins in a car park).
- **Measured:** at High, up to 2,090 draw calls and 6.1 million triangles (Leckhampton: about 370 and 3.7 million). On the Intel UHD 630 at Low, 35 fps (Leckhampton 54).
- **Woods:** OpenStreetMap marks 60 % of the square as woodland (107 km²), so the data is there; but the app's 26,000 trees spread over it stand about 12 times further apart than at Leckhampton, and the park looks like grassland with scattered trees.

So the app does need changes for a course this size, as the plan foresaw: dense woods near the road, and fewer draw calls and triangles far away. They are follow-up pull requests; this one adds the course and the builder changes.

## Checking

- Builder: Ruff, pytest (new tests for `fetch-hrdem`).
- The build's report: climbing near Ride with GPS's 630 m, and no ramps steeper than the parkways have (about 10 %).
- `validate`, `npm test`.
- Ride it: road on the ground everywhere, the start view, the credits.
- Screenshots: the three baselines don't change (the screenshot set stays at three; new courses are covered by the data checks).
