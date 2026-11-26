# Leckhampton Hill loop

An 11.8 km loop over the Cotswold scarp above Cheltenham, past the old quarries on Leckhampton Hill, dressed as the 19th-century hill: sheep on the high ground, hay stooks in the vale, smoke from the quarry.

## Sources

| Part                                                              | Source                                                                                                                                                                                                                                           | Licence                                                                                                    |
| ----------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ | ---------------------------------------------------------------------------------------------------------- |
| Route (`route.gpx`)                                               | Drawn along the roads on OpenStreetMap                                                                                                                                                                                                           | [ODbL 1.0](https://www.openstreetmap.org/copyright)                                                        |
| Ground and road heights (`terrain.bin`, `road.json`)              | Environment Agency [LiDAR Composite DTM](https://environment.data.gov.uk/survey): 2 m tiles along the road and 10 m around it, from the agency's coverage service (the dataset is named in `tools/coursebuilder/ea.py`), fetched with `fetch-ea` | [Open Government Licence v3.0](https://www.nationalarchives.gov.uk/doc/open-government-licence/version/3/) |
| Buildings, woods, single trees, hedges and walls (`scenery.json`) | OpenStreetMap, through the Overpass API                                                                                                                                                                                                          | [ODbL 1.0](https://www.openstreetmap.org/copyright)                                                        |

`build.json` records the rest: the exact command, the GPX's checksum, the 60 DTM tiles by name, and how current the OpenStreetMap data was. The course builder writes it on every build.

## Building it again

From the project folder, with the builder installed (see [docs/adding-a-course.md](../../docs/adding-a-course.md)):

```bash
.venv/bin/python -m tools.coursebuilder fetch-ea --route courses/leckhampton/route.gpx --out tools/.cache/ea-leckhampton
```

then run the `command` in `build.json` (with `.venv/bin/python` for `python`). The same tiles and map data give the same course, byte for byte. Newer OpenStreetMap data, or tiles the Environment Agency has since re-surveyed, give a slightly different one: check it in the ride and with the Leckhampton acceptance test (`COURSEBUILDER_NETWORK=1 .venv/bin/pytest tests/python/test_leckhampton.py`).

The route was exported from the course's road line when it was converted from the original ride's data, so it follows the road the original course used.
