# Screenshot tests

These tests load each built-in course at its normal start, in its normal weather, and compare the picture with a saved baseline, pixel for pixel. They are the safety net for refactoring: if a change is meant to leave the ride looking the same, these tests prove it.

They check the renderer, not the courses. The set stays fixed: the valley, Christmas, and Leckhampton as the one survey course. Adding a course does not add a screenshot; new courses are checked by the course data validator instead, which needs no browser.

## Running them

```bash
npm install
npx playwright install chromium   # once
npm run test:visual               # compare with the baselines
npm run test:visual:update        # write new baselines after a deliberate visual change
```

A full run takes about a minute. A failed comparison leaves the expected, actual and difference images in `test-results/`, and `npx playwright show-report` shows them side by side.

## Where the time goes

Comparing two images takes milliseconds. Nearly all the time is making the image: building the course's terrain and scenery in JavaScript (10–40 seconds), then rendering it in software. So keep the number of views small: each one costs a render, and each course costs a load.

## How they work

- **Software rendering.** The browser draws with SwiftShader, Chrome's software GPU, so every run gives exactly the same pixels. Real graphics cards and drivers do not. It is slow, several seconds of work per frame, which is why the timeouts are long.
- **Test options in the page.** `?freeze` stops the clock, so the rider, weather, wind and film grain hold still, builds all nearby verge grass in one frame, and stops drawing once a view is complete (`window.ride.held` becomes true). For looking at other spots by hand: `?at=<metres>` and `?weather=<name>` in the address bar, or `window.ride.go(metres)` and `window.ride.weather(name, true)` in the console.
- **No blur.** The tests turn off the blurred-glass effect behind the buttons (`backdrop-filter`), which takes software rendering over a minute to draw.

## Baselines

Baselines live in `screenshots/<platform>/`. Text renders differently on each operating system, so a baseline made on Linux will not match on macOS. Make baselines on the platform you test on, and treat Linux as the reference.

When a change is meant to alter the picture, update the baselines in the same pull request, look at the new images, and say in the pull request why they changed.
