# Plan: aerial photos on the ground

Today the ground is painted from rules: grass on the flats, rock on the steeps, a dark canopy colour where OpenStreetMap says there are woods. Up close, with the trees and verge grass on it, that works. From a lookout it doesn't: the Ottawa Valley from the Champlain Lookout, or the Severn vale from Leckhampton Hill, is a smooth green with dark patches. A real view is fields, roads, lakes, towns and forest edges. Real aerial photographs, laid over the ground we already build from the elevation data, would give the distance that detail.

Street View and Google's 3D tiles aren't used: their terms don't allow it, or the result is lumpy at road level, and they cost money per use.

## What riders see

- **Far away, the photograph.** Beyond a few hundred metres the ground's colour comes from the aerial photo: fields with their real shapes, lakes, villages, roads, forest.
- **Close up, the ground as now.** Near the road a photo at a few metres per pixel is a blur, and it has the real road, cars and shadows baked into it, so near the rider the ground stays the textured grass and rock it is now, with the 3D trees and verge grass on top. The photo's colour still tints it gently, so a field that is yellow from afar isn't bright green underfoot.
- **The golden hour stays.** Aerial photos are taken at midday. The builder evens out their colour and brightness, and the app lights them with the low sun like everything else. Their own baked-in shadows are short at midday, and at a distance they read as texture.
- **Courses without a photo look exactly as they do now**, the valley and Christmas courses included.

## Where the photos come from

Each needs a licence that allows sharing a derived image, and a credit on screen.

| Where                  | Source                                                                                                                                              | Detail    | Licence                       | Notes                                                                                                                                                                                 |
| ---------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------- | --------- | ----------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Québec (Gatineau Park) | [Imagerie orthorectifiée du Québec](https://www.donneesquebec.ca/recherche/fr/dataset/3eec3d05-61c1-4bcb-bf22-2d4bd71e2c0d), Gouvernement du Québec | 20–50 cm  | CC-BY 4.0                     | Downloaded tile by tile through a download map, with an index (GPKG) of the tiles. **Not yet checked**: whether it covers Gatineau Park (the service is down until 30 November 2026). |
| Anywhere               | Copernicus Sentinel-2 (level 2A, from the Earth Search STAC catalogue)                                                                              | 10 m      | Copernicus open data (credit) | Cloud-optimised GeoTIFFs through a STAC catalogue, like `fetch-hrdem`. Coarse, but enough for the far distance, which is where the photo shows. Pick a clear summer scene.            |
| United States          | USDA NAIP                                                                                                                                           | 60 cm–1 m | Public domain                 | For later.                                                                                                                                                                            |
| England (Leckhampton)  | To check                                                                                                                                            |           |                               | Aerial Photography for Great Britain isn't open. Sentinel-2 works meanwhile.                                                                                                          |

Every source goes into `docs/adding-a-course.md`'s table of sources, next to the elevation sources, with a column for aerial photos.

## How

### Course builder

- **`fetch-sentinel2`**: search the STAC catalogue for scenes over the course's square in a date range with little cloud, and read only the square from the best scene's red, green and blue bands (cloud-optimised, so no whole-scene downloads).
- **`fetch-quebec-ortho`**: find the tiles over the square in the index and download them into `tools/.cache/`, as `fetch-hrdem` does. Written once the service is back and its download links are known. If the links need the interactive map, the user downloads the tiles and the builder takes them as files, as it does for elevation data from other countries.
- **`build --imagery <files> --imagery-credit … --imagery-licence … --imagery-url …`**: reproject the photos onto the course's square (the same frame as `terrain.bin`, north up), and write **`ground.jpg`**:
  - sized for the square at about 3–4 m per pixel, at most 4096 × 4096 (every graphics chip we support can load that), so Gatineau's 13.4 km is 4096 pixels (3.3 m) and Leckhampton's 6.2 km is 2048 (3 m);
  - colour-evened: stretch and white-balance to a fixed range, so photos from different sources and days sit in the scene alike;
  - JPEG at a quality that keeps it under about 2.5 MB.
- `build.json` records the photos used (files, scene or tile names, dates), as it does the elevation tiles.

### Course format

- An optional `imagery` field in `course.json`: `{ "file": "ground.jpg", "size": 4096 }`. The photo covers the terrain square exactly, north edge at the top, like `terrain.bin`. Its credit goes in `credits` like every other source.
- Optional, so format 1 stays format 1: courses without it are unchanged. Both validators, `docs/course-format.md` and the shared cases in `tests/course-cases.json` change together.
- **Course size.** The rule of thumb of 5 MB per course becomes about 5 MB plus the photo (at most about 2.5 MB). The photo loads after the course starts: the ride starts at once with the ground as now, and the photo fades in when it arrives.

### The ride

- `src/course/terrain.js`: if the course has a photo, load it as a texture (with mipmaps and the best anisotropic filtering the chip allows) and look it up by the ground's x and z.
- In the ground's shader, the photo's colour takes over with distance: a light tint near the rider, all photo from about 400 m (High) or 250 m (Low). It replaces the canopy colour where there's a photo, since the photo shows the real forest.
- Lit as now: the photo stands in for the ground's colour, and the sun, the shading on the hills and the haze in the distance apply to it as they do today.
- Quality levels: the photo costs one texture lookup and its memory (about 21 MB on the graphics card at 4096 pixels, with mipmaps), so every level keeps it. If Low proves tight, it loads a half-size copy.

## Steps, one pull request each

1. **Builder and format**: `fetch-sentinel2`, `build --imagery`, the `imagery` field in both validators and the format document, with tests (reprojection onto the square, north up; the size rule; colour evening; the validators' shared cases).
2. **The ride**: load and blend the photo, fade it in when it arrives. Try it on Gatineau with a Sentinel-2 photo and compare views from the Champlain Lookout and the parkways, before and after.
3. **Gatineau's photo**: Québec's photos if they cover the park (`fetch-quebec-ortho`), otherwise keep Sentinel-2. Rebuild, credit, update the course README.
4. **Leckhampton**: Sentinel-2, unless an open English source turns up. Its screenshot test changes (compare by eye); the valley and Christmas screenshots don't change.
5. **Docs**: the sources table, `docs/adding-a-course.md`, `CLAUDE.md`'s course steps, and the README's list of changes.

## Checking

- Unit tests for the builder (Python) and the validators (both).
- `npm run test:visual`: valley and Christmas unchanged; Leckhampton changed only in the distance.
- `node tests/perf/measure.js` on the Intel chip at Low and on the NVIDIA card at High: no frame rate lost.
- By eye, on each course with a photo: the views from the high points, the fade between ground and photo (no visible line), and the start of the ride before the photo arrives.

## Questions to settle on the way

- Is Sentinel-2's 10 m good enough at Gatineau's distances, or does the park need Québec's photos to look right? Step 2 shows it.
- Do roads, car parks and buildings in the photo look wrong where they don't line up exactly with the road we draw? The near-road fade should hide that; if not, the builder can paint the photo's road out along our road line.
- Snow, or leafless trees, in a photo would fight the summer evening: the builder takes summer photos only.

## What happened

**1. Builder and format** (this pull request):

- `fetch-sentinel2` reads the course's square from the clearest summer scenes in the Earth Search catalogue (Sentinel-2 level 2A, its true-colour images), in a few seconds. For Gatineau one scene, 1 July 2024, covered the whole square.
- `build --imagery` writes `ground.jpg`. Gatineau's is 4096 pixels across (3.3 m each), 2.4 MB at JPEG quality 76; it lines up with the road along every parkway.
- **Colour.** Stretching each colour on its own, as planned ("white-balance"), turned the forest an unreal green and the lakes purple. The builder now stretches the brightness, red, green and blue together: dull photos are brought to a common range, and the colours stay true. Toning the summer green to the evening light is left to the ride (step 2).
- `build.json` records the photo's file and the scenes it was made from.

**2. The ride** (this pull request):

- The ground's shader takes its colour from the photo with distance, a little less vivid than the photo and brought to the ground's usual brightness, with the evening's shadows on it; a fifth of the ground's own colour still shows, so it sits in the scene. Nearer, the photo tints the ground lightly. The photo loads after the ride starts and fades in over 1.5 s; with `?freeze` the screenshot waits for it.
- **Distances.** All photo from about 250 m (High and Medium) or 200 m (Low), starting at 60–80 m, closer than planned (400 and 250 m): on Gatineau almost nothing beyond 450 m can be seen past the trees and the haze, so at the planned distances the photo hardly showed.
- **Memory.** A 4096-pixel photo takes about 90 MB of graphics memory with its mipmaps, not the 21 MB the plan said; Low loads a 2048-pixel copy (22 MB).
- **What it looks like.** Tried with Sentinel-2 photos (not committed). Gatineau: a modest change, since its road mostly runs between trees; where it opens out (41 km) the far ridge shows its fields and a quarry. Leckhampton's open vale shows its real field pattern clearly, but the July 2025 scene is mostly harvested fields, so the vale turns brown: a June scene (`--months 6-6`) may suit it better, to try in step 4.
- **Frame rate**: unchanged. Intel UHD 630 at Low: Gatineau 57 fps with the photo and without; Leckhampton 60 both. RTX 2060 at High: Gatineau 59.5 fps with, 56.3 without (later runs throttled by heat either way). The occasional freeze of over a second (see the course map plan) turned up in runs without the photo too.
- Courses without a photo draw exactly as before (their shader has none of the photo code): the screenshot tests are unchanged.
