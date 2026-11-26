## What and why

<!-- What does this change, and why? Link an issue if there is one. -->

## How it was tested

<!-- Which checks you ran (CONTRIBUTING.md), and what you tried in the ride. -->

- [ ] `npm run lint`, `npm run format:check` and `npm test` pass
- [ ] Ride code changed: `npm run test:visual` passes, or the baselines are updated and the reason is given above
- [ ] Course builder changed: `pytest` passes (and the Leckhampton acceptance test, if heights could change)

## New course? (delete if not)

- [ ] Built with the course builder, and `python -m tools.coursebuilder validate` passes
- [ ] The DTM is a terrain model (bare ground), not a surface model
- [ ] Every source is credited in `course.json`, each with its licence: heights, route (if drawn on someone's map), OpenStreetMap
- [ ] Each licence allows the data to be shared and published with the app
- [ ] Ridden round locally: the road sits on the ground, the start gives a good view, the credit line is complete
- [ ] The course folder is under about 5 MB, includes the `build.json` the builder wrote, and only `courses/<id>/` and `courses/index.json` change (no DTM files; a GPX only as `route.gpx`, from `--keep-route`)
- [ ] The route doesn't reveal anyone's home
