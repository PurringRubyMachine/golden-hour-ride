# Plan: a course map while riding

Riders can't see where they are on a loop, or what's coming. On Gatineau the distance display, which counts what you have ridden since the start (3 km in), read 14.4 km at the Champlain Lookout, where P3 is 17.4 km away, so the course looked shorter than it is.

## What it shows

A small panel in the bottom-right corner, above the credits:

- **The loop from above**, north up, fitted to the panel, with a dot for the rider and a small arrow for the direction of travel, and a tick where the course begins.
- **The height profile** of the whole loop underneath, with a line and dot at the rider's position, so the next climb is in sight; the lowest and highest heights at its side.
- **Where you are on the loop**: "17.4 of 41.0 km", measured from the course's beginning (for Gatineau, P3), whatever the start.

It hides with everything else (Hide info, H, "hide"), and a **Map** button (and the M key) turns it off and on, remembered in this browser like Hills and Quality.

## How

- `src/ui/map-geometry.js`, pure and unit-tested: fitting the loop into the panel (keeping its shape), a simplified outline (a point every ~20 m), the profile, and "where on the loop" from the ride's position `st.s`.
- `src/ui/course-map.js`: two canvases (outline and profile) drawn once when the course loads, and a small overlay redrawn four times a second from the frame loop, with the head unit's numbers. Sized for the screen's pixel ratio so it stays sharp. Costs next to nothing.
- The data is already loaded: the road's points every 1.5 m (`course/road.js`), with heights, and its length.
- Works for every course, the valley too.

## Checking

- Unit tests for the geometry.
- Ride: the dot follows the road on every course, including Skip and the Christmas valley; the panel at phone width doesn't cover the numbers; Hide info hides it; the Map button and M key toggle it and the choice is remembered.
- Screenshots change: the panel is in the picture. Compare and update the baselines.
- Frame rate unchanged at Low on the Intel chip.
