# Plan: a smooth ride on integrated graphics

## The problem

On a laptop's built-in Intel graphics, the ride stutters: most frames take 16.7 ms (60 fps), but about one in twenty takes most of a second, so it averages 8–9 fps and feels clunky. On a discrete graphics card (an RTX 2060) the same page holds 60 fps with no long frames, even at twice the resolution. Most riders' laptops have only the built-in graphics, so the ride must work there.

The cause is not the browser, Three.js or JavaScript: the JavaScript takes about 1 ms a frame. The graphics chip is given more work than it can do: too many pixels at full size, too much geometry, and shadows and post-processing that cost a lot whatever the size (see [After step 2](#after-step-2-what-limits-the-intel-chip)).

## What was measured

Chrome 158 on Ubuntu 22.04, 1920 × 1080, the valley at its start, 6 seconds after loading (Dell XPS 17: Intel UHD 630 and RTX 2060).

| Graphics, setting                             | Frames per second | Longest frame |
| --------------------------------------------- | ----------------: | ------------: |
| Intel UHD 630, as it is                       |               8.9 |         1.7 s |
| Intel, pixel ratio 1                          |               8.2 |         1.0 s |
| Intel, no post-processing                     |              12.0 |         1.1 s |
| Intel, no shadows                             |              10.5 |         0.9 s |
| Intel, no shadows and no post-processing      |              18.3 |         0.2 s |
| RTX 2060, valley or Leckhampton, any of these |                60 |         21 ms |

(The "pixel ratio 1" row changed nothing because the window's pixel ratio was already 1: it did not test fewer pixels. See [After step 2](#after-step-2-what-limits-the-intel-chip), which did.) Each frame draws **7.7 million triangles** in the valley and **6.1 million** at Leckhampton, counting the shadow pass:

| What                             | Valley              | Leckhampton          | Notes                                           |
| -------------------------------- | ------------------- | -------------------- | ----------------------------------------------- |
| Tree crowns                      | 7,000 × 300 = 2.1 M | 26,000 × 10 = 0.26 M | drawn again for shadows                         |
| Tree trunks                      | 7,000 × 24 = 0.17 M | 26,000 × 24 = 0.62 M | drawn again for shadows                         |
| Meadow (`meadow.js`)             | 260,000 × 8 = 2.1 M | the same             | far tufts shrink to nothing but are still drawn |
| Verge grass patches (`grass.js`) | about 0.4 M         | about 0.45 M         |                                                 |
| Terrain                          | 0.32 M              | 0.77 M               | drawn again for shadows                         |

Three things make it worse than it needs to be:

- **Nothing is culled.** Trees, meadow and verge patches set `frustumCulled = false`, because each is one mesh covering the whole course. So every tree is drawn every frame, behind the rider too.
- **The shadow pass draws the whole course.** The sun's shadow covers a 220 m square around the rider (`sky.js`), but every tree and the whole terrain are drawn into it, because nothing is culled.
- **Every tree is drawn in full** at every distance: a pine 3 km away gets the same 300 triangles as one beside the road, for a few pixels.

### After step 2: what limits the Intel chip

Tiling (step 2) cut the triangles a lot, but the frame rate hardly moved:

| Course      | Triangles before | After tiling | fps before | fps after |
| ----------- | ---------------: | -----------: | ---------: | --------: |
| Valley      |            7.7 M |        3.5 M |        8.6 |       9.2 |
| Christmas   |            5.2 M |        1.3 M |        9.7 |      10.6 |
| Leckhampton |            6.1 M |        3.7 M |        8.0 |       8.4 |

So geometry was not the main limit. Switching each cost off in turn (the valley after tiling, Intel UHD 630):

| Window      | What was switched off                      |  fps | Longest frame |
| ----------- | ------------------------------------------ | ---: | ------------: |
| 1920 × 1080 | nothing                                    |    8 |         1.5 s |
| 1920 × 1080 | shadows                                    |   11 |         1.1 s |
| 1920 × 1080 | post-processing                            |   13 |         0.9 s |
| 1920 × 1080 | anti-aliasing / bloom / light shafts, each | 9–10 |     0.6–1.4 s |
| 1920 × 1080 | meadow (2 M triangles)                     |    8 |         0.9 s |
| 1920 × 1080 | trees                                      |   11 |         0.7 s |
| 1920 × 1080 | post-processing, shadows, meadow and trees |   31 |        0.17 s |
| 960 × 540   | nothing                                    |   16 |         0.6 s |
| 640 × 360   | nothing                                    |   21 |         0.4 s |
| 960 × 540   | post-processing, shadows and meadow        |   60 |         17 ms |

- **Pixels matter most.** At full size, with almost nothing drawn (370,000 triangles), the chip still manages only 31 fps: the ground, sky, road and lighting cost too much per pixel at 1920 × 1080.
- **Shadows and post-processing have a fixed cost too**: even at 640 × 360 with everything on, it's 21 fps.
- **Fewer pixels and fewer effects together** give a steady 60.

So the biggest lever is drawing fewer pixels on slow chips (a render scale below 1), with cheaper shadows and effects. That is now step 3; distant trees as pictures (formerly step 3) are now step 4, done only if the measurements after step 3 still call for it.

## Goals

- Intel UHD 630 (and similar: Iris Xe, AMD's built-in Radeon) at 1920 × 1080: a steady 60 fps on the automatic setting, with no frame over 50 ms after the start. On a chip as slow as the UHD 630 that may mean Low.
- A discrete card: looks as it does now.
- No visible pop: things that change detail with distance do so gradually or where it can't be seen.
- Screenshot tests keep working, with any baseline changes deliberate and explained.

## The work

### 1. Measure (no change to the picture)

- `window.ride.stats`: draw calls and triangles for the last frame, counted across all passes (`renderer.info` with `autoReset` off, reset at the start of each frame). Cheap enough to leave on.
- `tests/perf/measure.js`: a Playwright script that opens the ride in a visible Chrome (headless Chrome won't use the real graphics chip on Linux), lets it settle, and prints frames per second, the median, 95th-percentile and longest frame, and `ride.stats`, for each course. Run by hand, not in CI (CI has no graphics chip). `tests/perf/README.md` says how, including how to choose the Intel or NVIDIA chip on a hybrid laptop.
- Record the numbers above as the baseline, and re-measure after each step.

### 2. Cut the course into tiles, so culling works (no change to the picture)

- **Trees**: group the tree positions into 250 m tiles, one `InstancedMesh` per tile (crowns and trunks), each with its own bounding sphere and `frustumCulled` on. Three.js then skips tiles outside the camera's view, and, separately, tiles outside the shadow's 220 m square in the shadow pass. Positions, sizes and colours are generated exactly as now, in the same order from the same random stream, and only then sorted into tiles, so every tree stays where it is.
- **Terrain**: split the ground mesh into tiles the same way (8 × 8), sharing its vertex data, so it is culled in both passes too.
- Expected: about 7.7 M → 3 M triangles in the valley (half the trees are behind the rider, and nearly all fall outside the shadow square). The screenshots should match exactly; if a few pixels differ from the drawing order changing, look, and update the baselines only if nothing visible has changed.

### 3. Quality settings, chosen automatically

A new module, `src/render/quality.js`, with three levels. Every setting in them can change while riding, so the automatic choice never needs a reload:

| Setting                                      | Low    | Medium       | High (as now)         |
| -------------------------------------------- | ------ | ------------ | --------------------- |
| Render scale (pixels drawn per screen pixel) | 0.5    | 0.7          | the screen's, up to 2 |
| Shadows                                      | off    | 2048², sharp | 4096², soft           |
| Bloom and light shafts                       | off    | on           | on                    |
| Anti-aliasing (MSAA)                         | off    | 2×           | 4×                    |
| Meadow tufts                                 | 60,000 | 130,000      | 260,000               |
| Verge grass out to                           | 140 m  | 200 m        | 230 m                 |

The render scale is the big one. Below 1, the picture is drawn smaller and the browser stretches it to the window, so it is a little softer; the head unit and buttons are not part of it and stay sharp. On a high-resolution laptop screen (pixel ratio 2), Medium draws an eighth of the pixels High does.

(The lens pass, which does rain drops on the lens and the painted look, stays at every level: it is cheap, and the weather depends on it.)

- **Automatic** is the default. It starts at Medium on built-in graphics (the renderer's name says "Intel", "Mesa", "Iris", "Radeon Graphics" or "Apple"), otherwise High. After loading, it watches the frames: if more than 10 % of frames over 3 seconds take longer than 20 ms, it steps down a level; if every frame for 20 seconds is under 12 ms, it may step back up once. Never more than one step every 5 seconds, so it doesn't seesaw.
- **A Quality control** beside Hills: Auto, Low, Medium, High, remembered in this browser like Hills. `?quality=` sets it for one visit.
- **Screenshot tests** use `?quality=high` (and so does `?freeze` unless told otherwise), so the baselines don't depend on the machine.
- Meadow: draw the first _n_ tufts by setting `instanceCount` (the tufts are already in random order, so any first _n_ are spread evenly), and widen each tuft a little at lower counts so the field stays green.

### 4. Draw distant trees simply (if still needed)

Only if, after step 3, Medium on the Intel chip still drops frames because of trees (measured by switching them off), or High on a mid-range card does.

- **Far trees as pictures.** At start-up, render each tree kind (pine, snowy pine, broadleaf) once, from the side, into a small texture. Beyond a distance (`treeFar`, about 400 m) a tile draws its trees as two crossed quads with that picture (4 triangles, not 300), lit and fogged the same way. Tiles switch whole, and the switch is hidden by fading over 50 m (the picture and the full tree overlap with dithered transparency, which costs nothing extra with `alphaTest`).
- **Trunks** stop beyond about 250 m: at that distance a trunk is under the crown and a pixel wide.
- **Shadows from near trees only**: tiles beyond the shadow square don't cast anyway after step 2; pictures never cast shadows.
- Expected: valley 3.5 M → under 1 M triangles; Leckhampton likewise (its trunks are its biggest cost). This changes the far scenery slightly, so the three baselines are updated, after comparing the old and new pictures by eye.

### 5. Docs and guard rails

- `docs/architecture.md`: tiles, distances and quality levels; a triangle budget (about 1.5 M at Medium) for anyone adding scenery.
- `CONTRIBUTING.md`: for changes to scenery or rendering, run `tests/perf/measure.js` on built-in graphics if you can, and give the numbers in the pull request.
- A unit test of the automatic choice (feed it frame times, check its steps), with the logic kept free of Three.js.

## Pull requests

So that the change that mustn't alter the picture is reviewed alone:

1. **Steps 1 and 2**: measuring, and tiles. Screenshots match (but for 3 pixels, from the drawing order). Numbers before and after in the description.
2. **Steps 3 and 5**: quality settings and docs. Baselines unchanged (the tests use High).
3. **Step 4**, if needed: distant trees, with baselines updated and before-and-after pictures.

## Risks

- **Pop-in at tile edges.** Tiles switching to pictures can show a line moving across a forest. The dithered fade over 50 m should hide it; if not, switch per tree in the vertex shader instead (costs nothing on the CPU, saves less on the GPU).
- **The picture of a tree looks flat** when the road turns past it. Crossed quads look right from any side at a distance; nearer than about 300 m they wouldn't, which is why `treeFar` starts at 400 m on High.
- **The automatic choice misjudges** a busy moment (loading, a weather change) as slowness. It ignores the first 5 seconds and the frames during a weather change.
- **Shadow pass culling and the moving shadow square**: Three.js culls each pass against its own camera, so this needs no code, but check that trees at the edge of the square still cast shadows into it (bounding spheres must include the crown).
- **Christmas fairy lights** are positioned from the trees: they must still follow the trees after the tiling (they're built from the same positions, so they should).

## Not doing

- **A different engine or language** (Unity, Godot, native): the measurements show the page itself is fast on a capable chip; the fix is drawing less, which any engine would need too.
- **WebGPU**: it lowers the JavaScript cost of each draw call, which is already about 1 ms. Not worth it yet, and it is behind a setting in Chrome on Linux.
- **Changing what the scenery is** (fewer trees, smaller woods). The aim is the same picture for less work.

## Decided

- The Quality control goes on the main bar, beside Hills, until there are more settings.
- A rider on Low sees no note suggesting a better computer.
