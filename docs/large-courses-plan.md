# Plan: large courses that look and run right

Gatineau Park Loop (41 km, a 13.4 km terrain square) showed two problems that courses the size of Leckhampton (6.2 km) don't have. This plan fixes both, measured on the Intel UHD 630 as before (`tests/perf/measure.js`).

## Where things stand

| Course      | Low: fps | calls | triangles | High: calls | triangles |
| ----------- | -------: | ----: | --------: | ----------: | --------: |
| Valley      |       60 |    78 |     1.4 M |         131 |     3.5 M |
| Leckhampton |       60 |   206 |     1.1 M |         391 |     3.7 M |
| Gatineau    |       38 | 1,062 |     3.4 M |       2,079 |     6.0 M |

(High runs at 8–10 fps on this chip on every course, as before: Auto chooses Low there.)

## 1. Woods: dense near the road, and woodland that reads as forest from afar

**The problem.** A surveyed course gets at most 26,000 trees (`trees.js`), placed at random over all the woodland in the square. Leckhampton's woods total about 5 km², so they are dense. Gatineau's total 107 km² (60 % of the square), so the same trees stand about 12 times further apart, and the park looks like grassland with scattered trees.

**The fix.**

- **Where the woodland is small enough** for the trees to be dense everywhere (at least 3,000 per km² of woodland), trees are placed as now, in the same order from the same random stream: Leckhampton doesn't change.
- **Otherwise, trees are placed near the road**: pick a point along the road and a side at random, and a distance from the road that is usually short and sometimes long (11 m plus an exponential with a 150 m mean, up to 1.5 km), and keep it if the map says woodland there and there's no building. Riders see woods densely along the road, thinning into the distance, for the same 26,000 trees.
- **Woodland ground looks like forest from afar.** The terrain gets the woodland mask as a vertex attribute, and beyond about 150 m from the camera wooded ground is coloured as a dark canopy, fading in with distance, so hillsides of forest read as forest, where there are too few trees to cover them. Close up it stays ground, under the trees. This applies to every surveyed course (Leckhampton's distant woods too), so its screenshot changes; compare by eye.

## 2. Distant ground and trees: less detail, fewer draw calls

**The problem.** At Low, Gatineau draws 3.4 million triangles, mostly ground: the terrain is 1,340 × 1,340 cells, all at full detail wherever a tile is in view. And it makes over 1,000 draw calls, from hundreds of 250 m tree tiles.

**The fix.**

- **Terrain at three levels of detail.** Each terrain tile is drawn with every grid point (near), every second (middle distance) or every fourth (far), chosen each frame by its distance from the camera. A coarser tile's edges keep every grid point, joined to its coarser middle by a strip of triangles, so neighbouring tiles at different levels meet without cracks. Large terrains get smaller tiles (at most 100 cells across, about 1 km), so the choice is fine-grained enough. The distances depend on the quality level: on High, full detail out to 1.5 km and half to 3.5 km; on Low, 0.8 and 2 km.
- **Tree tiles sized to the course**: 250 m, or larger on large courses (an area of at most about 24 × 24 tiles), so a big square doesn't mean thousands of draw calls. With trees concentrated along the road (1), most tiles away from it are empty and not drawn at all.
- Measure after each; drawing distant trees as pictures (the performance plan's step 4) stays deferred unless the numbers still call for it.

## Goals

- Gatineau at Low on the Intel UHD 630: a steady 60 fps, under about 1.5 million triangles and a few hundred draw calls.
- Gatineau's park looks forested from the road, near and far.
- Valley, Christmas and Leckhampton: no slower; Leckhampton and the valley look the same up close (their screenshots may change in the distance, compared by eye).

## Pull requests

1. Woods near the road, and the woodland canopy colour.
2. Terrain levels of detail, and tree tile sizing.

## What happened

**1. Woods** (pull request 14): Gatineau now looks like a wooded parkway, dense along both sides. Its draw calls at Low fell from 1,062 to 570, but it still ran at 37 fps: the ground was the limit.

**2. Distance** (this pull request): the terrain's levels of detail took Gatineau to 51 fps at Low (1.23 million triangles, from 3.4). Switching things off one at a time then showed trees, and the verge grass, as the remaining cost, so two more settings were added:

- **Trees out to a distance**: at Low, tree tiles beyond 1 km are not drawn (Medium: 2 km; High: all). Beyond that the woods carry on as the ground's canopy colour from the first pull request, which is what makes this look right.
- **Tree and verge grass density**: Low draws 60 % of the trees and half the verge grass (Medium: all the trees, 80 % of the grass). Both were placed at random, so drawing the first part of each list thins them evenly; the Christmas valley keeps every tree, because its fairy lights are wound round them.

| Course (Intel UHD 630, Low) | Before: fps | calls | triangles | After: fps | calls | triangles |
| --------------------------- | ----------: | ----: | --------: | ---------: | ----: | --------: |
| Valley                      |          60 |    78 |     1.4 M |         60 |    65 |     0.7 M |
| Christmas                   |          60 |    81 |     1.0 M |         60 |    68 |     0.6 M |
| Leckhampton                 |          60 |   206 |     1.1 M |         60 |    79 |     0.6 M |
| Gatineau                    |          38 | 1,062 |     3.4 M |         60 |   143 |     0.9 M |

Tree tiles are larger on large courses (an area of at most about 24 × 24 tiles: 435 m on Gatineau, still 250 m elsewhere).

## Not doing here

- **Out-and-back spurs.** The builder removes them (they are usually GPS noise, and the ride can't turn round: the road would overlap itself). On Gatineau that drops the 300 m into the Champlain Lookout car park and back, so the loop is 41.0 km, not Ride with GPS's 41.7 km. Riding into a dead end and turning would need the road drawn twice and a U-turn: a separate change, if wanted.
- **The distance display** counts what you have ridden since the start, so on Gatineau (which starts 3 km in) it reads 3 km less than the distance from P3. A course map showing where you are on the loop is proposed separately.
