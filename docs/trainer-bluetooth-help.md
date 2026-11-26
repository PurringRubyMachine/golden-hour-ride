# Plan: say why a trainer can't connect

## The problem

On Ubuntu 22.04 with Google Chrome, "Connect trainer" says "Needs Chrome or Edge". The browser is Chrome, so the message is wrong.

The trainer code checks only whether `navigator.bluetooth` exists, and assumes the browser lacks Web Bluetooth if it doesn't. But Chrome hides `navigator.bluetooth` for other reasons too:

- **Chrome on Linux** ships Web Bluetooth switched off. It comes on with _Experimental Web Platform features_ (`chrome://flags/#enable-experimental-web-platform-features`) and a relaunch. This is the Ubuntu case.
- **Insecure pages**: Web Bluetooth only exists on https or `localhost`. A ride opened as `http://192.168.1.20:8791/` from another machine has none, whatever the browser.
- **Brave and some other Chromium builds** turn it off by default.

## The fix

1. A new pure module, `src/devices/bluetooth-help.js`: `bluetoothHelp({ bluetooth, secure, userAgent })` returns `null` when Web Bluetooth is there, otherwise `{ label, title, steps }` for the likely cause, in this order: insecure page; Chromium on Linux (not Android or ChromeOS); Brave; another Chromium browser; any other browser (Firefox, Safari), which needs Chrome or Edge.
2. In `trainer.js`, when Bluetooth is missing, "Connect trainer" opens a drop-down panel (the existing `panel()` helper, so it closes the log or course menu) with what to do, instead of changing its own label.
3. Unit tests for each case, with real user agent strings, in `tests/unit/bluetooth-help.test.js`.
4. README: a line on Linux under the trainer section.

The voice button's "needs Chrome or Edge" stays: speech recognition really isn't in Firefox, and it doesn't depend on a flag in Chrome on Linux.

5. Found on the way: at 1280 px the controls wrap onto two rows, and every drop-down panel (log, courses, this one) opened on top of the second row, covering Log and Hide info. `panel()` now opens each one just below the controls.

## Checking

Unit tests; then in Chrome on Ubuntu, with the flag off (the panel shows the Linux steps) and on (the trainer list appears).

The screenshot tests' browser has no Web Bluetooth, so its button now reads "Trainer: turn on Bluetooth" instead of "Connect trainer". The three baselines change in the controls only; the scenes are identical.
