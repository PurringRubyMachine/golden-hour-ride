# Adding a course

Turn a road you know into a course: a route as GPX, the ground under it as a LiDAR DTM, and the course builder does the rest. This takes about half an hour the first time, most of it finding and downloading the DTM.

The format the builder writes is described in [course-format.md](course-format.md).

New to this? [Claude Code](https://code.claude.com/docs/en/quickstart) can do these steps for you from a route link and a terrain source: see [Add your own course, with Claude Code](../README.md#add-your-own-course-with-claude-code) in the README. This guide is what it follows (with the project's [CLAUDE.md](../CLAUDE.md)), and what to do by hand.

## 1. The route

You need a GPX file of the loop: a track, or a route.

- **Draw it** on a route planner such as [gpx.studio](https://gpx.studio/), following the roads, and export it as GPX. Planners draw over OpenStreetMap, so credit it (see step 4).
- **Or use a ride you recorded.** The builder takes only the positions: not times, heart rate or anything else. Only the road line ends up in the course, but that does show where the loop goes, so pick a loop that doesn't start at your door.

The course must be a **loop**: finish where you started. If the ends are more than 50 m apart the builder stops; pass `--close` to join them with a straight line, which is fine for a short gap on the same road.

Long loops make large courses. Up to about 25 km works well; the terrain square grows with the loop's extent.

## 2. The DTM

You need a **DTM** (digital terrain model: the bare ground), not a DSM (which includes buildings and trees, so roads would climb over every hedge). Aim for 1 or 2 m resolution: the road's gradient comes from it. Cover the route plus about 1.3 km on every side (the builder's `--margin`), so the hills around the road are there to see.

Any raster GDAL can read works: GeoTIFF (any compression), ASCII grid, IMG, VRT and others, in any coordinate system, as many files as it takes. Mixed resolutions are fine: where files overlap, the finest wins.

Free sources (check each source's own terms; the licence identifiers here are for `--heights-licence`):

| Where         | Source                                                                                                                       | Licence                      |
| ------------- | ---------------------------------------------------------------------------------------------------------------------------- | ---------------------------- |
| England       | Environment Agency LiDAR Composite DTM ([survey portal](https://environment.data.gov.uk/survey)): use `fetch-ea`             | `OGL-UK-3.0`                 |
| Scotland      | [Scottish Remote Sensing Portal](https://remotesensingdata.gov.scot/)                                                        | `OGL-UK-3.0`                 |
| Wales         | [DataMapWales](https://datamap.gov.wales/) LiDAR                                                                             | `OGL-UK-3.0`                 |
| Canada        | NRCan [HRDEM](https://open.canada.ca/data/en/dataset/0fe65119-e96e-4a57-8bfe-9d9245fba06b) (CanElevation): use `fetch-hrdem` | `OGL-Canada-2.0`             |
| United States | USGS 3DEP, from [The National Map downloader](https://apps.nationalmap.gov/downloader/)                                      | Public domain                |
| France        | IGN [RGE ALTI](https://geoservices.ign.fr/rgealti)                                                                           | `etalab-2.0`                 |
| Switzerland   | swisstopo [swissALTI3D](https://www.swisstopo.admin.ch/en/height-model-swissalti3d)                                          | Free use, credit "swisstopo" |
| Netherlands   | [AHN](https://www.ahn.nl/)                                                                                                   | `CC0-1.0`                    |
| Denmark       | [Dataforsyningen](https://dataforsyningen.dk/) (DHM)                                                                         | See the site                 |
| Norway        | [Høydedata](https://hoydedata.no/)                                                                                           | `CC-BY-4.0`                  |
| Spain         | CNIG [Centro de Descargas](https://centrodedescargas.cnig.es/) (MDT)                                                         | `CC-BY-4.0`                  |

Only data you're allowed to share can go in a course: the course contains heights derived from it and is published with the app.

## 3. Install the builder

Python 3.10 or later. From the project folder:

```bash
python3 -m venv .venv
.venv/bin/pip install -r tools/requirements-dev.txt
```

That includes GDAL (inside rasterio's wheels), so there's nothing else to install. If pip can't find a rasterio wheel for your system, `conda install -c conda-forge rasterio pyproj` works everywhere.

## 4. Build

```bash
.venv/bin/python -m tools.coursebuilder build \
    --id my-loop --name "My Loop" --short-name "My Loop" \
    --route my-loop.gpx --dtm path/to/dtm/ \
    --heights-credit "Heights: <source>, <licence name>." --heights-licence <licence id> --heights-url <source's page>
```

`--dtm` takes files or folders. The builder:

1. reads the GPX, removes out-and-back spurs, and resamples the loop every 5 m;
2. picks a coordinate system to work in: the DTM's own if it's in metres and true to scale there, otherwise the local UTM zone;
3. finds the road surface across the road every 5 m, draws it straight across the bridges OpenStreetMap marks (the DTM is the ground beneath them), smooths it, and reports the climbing and steepest gradients;
4. builds a 10 m terrain grid, filling small holes;
5. fetches buildings, woods, single trees, hedges and walls from OpenStreetMap (`--no-osm` to skip), and credits OpenStreetMap;
6. writes `courses/my-loop/`, adds it to `courses/index.json`, and validates it.

Read what it prints. Climbing and gradients should be what you'd expect of the road; a 40 % ramp on a lane means something is wrong (often a DSM instead of a DTM, or a bridge missing from OpenStreetMap). If it warns that the GPX's points are far apart, the file is a list of turns rather than a track: export the track instead (on Ride with GPS, "GPX Track", not "GPX Route").

Credit every source: add `--credit "Route drawn on OpenStreetMap|ODbL-1.0|https://www.openstreetmap.org/copyright"` if you drew the route over OpenStreetMap, and anything else you used.

Other options (`build --help` lists them all):

| Option                            | Does                                                                                         |
| --------------------------------- | -------------------------------------------------------------------------------------------- |
| `--start METRES`                  | Where riders begin, along the loop from its first point. Pick somewhere with a view.         |
| `--keep-route`                    | Copy the GPX into the course as `route.gpx`, so others can rebuild it. See below.            |
| `--scenery-style pastoral-1800s`  | Sheep on the high ground and hay stooks in the vale, as at Leckhampton.                      |
| `--sheep-above`, `--stooks-below` | The heights for those, in metres (by default the road's 65th and 35th percentiles).          |
| `--smoke LAT,LON`                 | Smoke from the steepest ground near a point, such as a quarry. Repeatable.                   |
| `--margin METRES`                 | Terrain around the route (1300). Smaller for a long loop or a DTM that doesn't reach so far. |
| `--description TEXT`              | A sentence for the course file.                                                              |
| `--imagery FILE...`               | A photo of the ground from above, shown in the distance. See below.                          |

Rebuilding with the same `--id` replaces the course. Downloads are cached in `tools/.cache/`, so a rebuild is quick.

Every build also writes `build.json` into the course folder: the exact command, the GPX's checksum, the DTM files by name, and how current the OpenStreetMap data was. Commit it with the course: it's how anyone can tell where the course came from. Paths in it are relative to the project folder, or just file names if the files are elsewhere, so nothing from your home folder is published.

**Keeping the route.** With `--keep-route` the GPX is copied into the course as `route.gpx`, and `build.json`'s command uses that copy, so anyone can rebuild the course. Use it for a route anyone could ride and you're happy to publish, such as a loop drawn on a route planner. Leave it off for a recording of your own ride: the road line in the course shows the loop either way, but a GPX can carry more, and you may not want it published. [courses/leckhampton/](../courses/leckhampton/) is an example, with a README on its sources.

### Example: England

`fetch-ea` downloads the Environment Agency DTM for a route (2 m tiles along the road, 10 m around it) and prints the credit options to use:

```bash
.venv/bin/python -m tools.coursebuilder fetch-ea --route my-loop.gpx --out tools/.cache/ea-my-loop
.venv/bin/python -m tools.coursebuilder build --id my-loop --name "My Loop" --route my-loop.gpx \
    --dtm tools/.cache/ea-my-loop \
    --heights-credit "Heights: Environment Agency LiDAR, Open Government Licence." \
    --heights-licence OGL-UK-3.0 --heights-url https://environment.data.gov.uk/survey
```

The service is free and sometimes slow; `fetch-ea` waits and tries again, and only fetches tiles it doesn't have.

### Example: Canada (HRDEM)

`fetch-hrdem` reads Natural Resources Canada's [HRDEM](https://open.canada.ca/data/en/dataset/0fe65119-e96e-4a57-8bfe-9d9245fba06b) terrain model for a route (2 m tiles along the road, 10 m around it) and prints the credit options to use. The mosaics are cloud-optimised files of whole provinces; it reads only the pieces the route needs, in seconds:

```bash
.venv/bin/python -m tools.coursebuilder fetch-hrdem --route my-loop.gpx --out tools/.cache/hrdem-my-loop
.venv/bin/python -m tools.coursebuilder build --id my-loop --name "My Loop" --route my-loop.gpx \
    --dtm tools/.cache/hrdem-my-loop \
    --heights-credit "Heights: Natural Resources Canada HRDEM, Open Government Licence – Canada." \
    --heights-licence OGL-Canada-2.0 \
    --heights-url https://open.canada.ca/data/en/dataset/0fe65119-e96e-4a57-8bfe-9d9245fba06b
```

[courses/gatineau-park-loop/](../courses/gatineau-park-loop/) was built this way. The HRDEM mosaic is in Canada Atlas Lambert (EPSG:3979), which stretches distances by about half a percent in southern Canada; the builder sees that and works in the local UTM zone instead, so the road's length and gradients come out right. Heights are CGVD2013, which doesn't matter: the ride only uses differences in height.

### The ground from above

A photo of the ground, from a satellite or a plane, shows real fields, lakes, villages and forest in the distance, where the ground's own colours are a smooth green. `fetch-sentinel2` reads one for any route from Copernicus Sentinel-2 (10 m per pixel, free with credit): the clearest summer scenes of the last three years, filling any part one misses from the next, in a few seconds. Look at the file it writes before building with it: a scene can still have a patch of cloud or haze the catalogue missed.

```bash
.venv/bin/python -m tools.coursebuilder fetch-sentinel2 --route my-loop.gpx --out tools/.cache/s2-my-loop
.venv/bin/python -m tools.coursebuilder build ... \
    --imagery tools/.cache/s2-my-loop/sentinel2.tif \
    --imagery-credit "Ground from above: contains modified Copernicus Sentinel data 2024." \
    --imagery-licence "Copernicus Sentinel data licence" \
    --imagery-url https://sentinels.copernicus.eu/documents/247904/690755/Sentinel_Data_Legal_Notice
```

`fetch-sentinel2` prints the credit for the years it used. `--months` (6-8 by default: June to August, before the leaves turn) and `--years` choose other seasons and years; `--max-cloud` allows cloudier scenes where clear ones are rare. Pass the same `--margin` as to the build.

Any colour GeoTIFF with a coordinate system will do instead, such as a government aerial photo, if its licence allows sharing a derived image. The builder turns it onto the course's square, evens out its brightness and writes `ground.jpg` (at most 4096 pixels across and about 2.5 MB).

## 5. Ride it

```bash
npm start                                   # or: python3 -m http.server 8791
```

Open `http://localhost:8791/?course=my-loop`, or pick it from the Course menu. Ride round: skip along with → and ← to check the whole loop. Things to look at:

- Does the road sit on the ground everywhere, without steps or spikes?
- Does the start (`--start`) give a good first view?
- Do the woods, hedges and fields look right?
- Is the credit line at the bottom right complete?

## 6. Check and share

```bash
.venv/bin/python -m tools.coursebuilder validate
npm test                                    # includes validating every course
```

Then open a pull request with `courses/my-loop/` (including `build.json`) and the change to `courses/index.json`. Don't add the DTM, or a GPX outside the course folder. The pull request template has a checklist for new courses: credits, licences, size, and that you've ridden it. See [CONTRIBUTING.md](../CONTRIBUTING.md) for the rest.
