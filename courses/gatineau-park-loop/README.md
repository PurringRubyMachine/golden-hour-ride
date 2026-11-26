# Gatineau Park Loop

A 41 km loop into Gatineau Park, Quebec: from parking P3 (Gamelin) up the Gatineau and Champlain Parkways to the Champlain Lookout over the Ottawa Valley (345 m), and back by the Fortune and Gatineau Parkways. About 670 m of climbing. Riders start 3 km in, on the Gatineau Parkway.

## Sources

| Part                                                 | Source                                                                                                                                                                                                                    | Licence                                                                                      |
| ---------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------- |
| Route                                                | ["Gatineau Park Loop"](https://ridewithgps.com/routes/34405323) on Ride with GPS (route 34405323), along roads mapped in OpenStreetMap                                                                                    | [ODbL 1.0](https://www.openstreetmap.org/copyright), for the roads                           |
| Ground and road heights (`terrain.bin`, `road.json`) | Natural Resources Canada [HRDEM](https://open.canada.ca/data/en/dataset/0fe65119-e96e-4a57-8bfe-9d9245fba06b) mosaic (1 m DTM, mosaics `8_2` and `9_2`), read at 2 m along the road and 10 m around it with `fetch-hrdem` | [Open Government Licence – Canada](https://open.canada.ca/en/open-government-licence-canada) |
| Buildings, woods, trees (`scenery.json`); bridges    | OpenStreetMap, through the Overpass API (bridges shape the road's heights)                                                                                                                                                | [ODbL 1.0](https://www.openstreetmap.org/copyright)                                          |

The route's GPX isn't in the repository: it is the route author's, to publish or not. `build.json` records its checksum, the HRDEM tiles used, how current the OpenStreetMap data was, and the build command.

## Building it again

1. Get the route as a GPX **track**: on the route's page, signed in, export "GPX Track" (not "GPX Route", which has only the 14 turns). Or build one from the route's public JSON (`https://ridewithgps.com/routes/34405323.json`: its `track_points` have `y` latitude and `x` longitude). Save it as `tools/.cache/gatineau-park-loop.gpx`; `build.json`'s checksum says whether it is the same file.
2. Read the heights (about 40 MB, in seconds):

   ```bash
   .venv/bin/python -m tools.coursebuilder fetch-hrdem --route tools/.cache/gatineau-park-loop.gpx --out tools/.cache/hrdem-gatineau --margin 800
   ```

3. Run the `command` in `build.json` (with `.venv/bin/python` for `python`).

## Notes

- **Size.** At 41 km this is the longest course: an 800 m margin (not the usual 1300 m) keeps it to 3.9 MB.
- **Bridges.** The terrain model is bare ground, so the builder draws the road straight across the four bridges OpenStreetMap marks on the route. Without that, the road dipped 3–4 m into the valleys beneath them, at 20 %.
- **Woods.** The park is mostly forest (60 % of the terrain square is woodland in OpenStreetMap), but the app plants at most 26,000 trees on a course, spread over all its woodland, so here they stand far apart. A later change to the app is planned to keep woods dense near the road.
