# Screenshot tests

These tests load each course at fixed spots and weathers and compare the picture with a saved baseline, pixel for pixel. They are the safety net for refactoring: if a change is meant to leave the ride looking the same, these tests prove it.

## Running them

```bash
npm install
npx playwright install chromium   # once
npm run test:visual               # compare with the baselines
npm run test:visual:update        # write new baselines after a deliberate visual change
```

A full run takes about five minutes. A failed comparison leaves the expected, actual and difference images in `test-results/`, and `npx playwright show-report` shows them side by side.

## How they work

- **Software rendering.** The browser draws with SwiftShader, Chrome's software GPU, so every run gives exactly the same pixels. Real graphics cards and drivers do not. It is slow, several seconds of work per frame, which is why the timeouts are long.
- **Test options in the page.** `?freeze` stops the clock, so the rider, weather, wind and film grain hold still, builds all nearby verge grass in one frame, and stops drawing once a view is complete (`window.ride.held` becomes true). `window.ride.go(metres)` moves along the road and draws again. `window.ride.weather(name, true)` switches the weather instantly. `?at=<metres>` and `?weather=<name>` do the same from the address bar.
- **No blur.** The tests turn off the blurred-glass effect behind the buttons (`backdrop-filter`), which takes software rendering over a minute to draw.

## Baselines

Baselines live in `screenshots/<platform>/`. Text renders differently on each operating system, so a baseline made on Linux will not match on macOS. Make baselines on the platform you test on, and treat Linux as the reference.

When a change is meant to alter the picture, update the baselines in the same pull request, look at the new images, and say in the pull request why they changed.
