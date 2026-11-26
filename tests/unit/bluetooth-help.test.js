import { test } from 'node:test';
import assert from 'node:assert/strict';
import { bluetoothHelp } from '../../src/devices/bluetooth-help.js';

const UA = {
  chromeLinux: 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/158.0.0.0 Safari/537.36',
  chromeWin:
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/158.0.0.0 Safari/537.36',
  chromeAndroid:
    'Mozilla/5.0 (Linux; Android 14; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/158.0.0.0 Mobile Safari/537.36',
  chromeOS:
    'Mozilla/5.0 (X11; CrOS x86_64 14541.0.0) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/158.0.0.0 Safari/537.36',
  edgeLinux:
    'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/158.0.0.0 Safari/537.36 Edg/158.0.0.0',
  firefoxLinux: 'Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:140.0) Gecko/20100101 Firefox/140.0',
  safari:
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.0 Safari/605.1.15',
};
const help = (userAgent, more = {}) => bluetoothHelp({ bluetooth: undefined, secure: true, userAgent, ...more });

test('nothing to say when Web Bluetooth is there', () => {
  assert.equal(bluetoothHelp({ bluetooth: {}, secure: true, userAgent: UA.firefoxLinux }), null);
});

test('Chrome and Edge on Linux: turn on the flag', () => {
  for (const ua of [UA.chromeLinux, UA.edgeLinux]) {
    const h = help(ua);
    assert.match(h.title, /Linux/);
    assert.ok(h.steps.some((s) => s.includes('chrome://flags/#enable-experimental-web-platform-features')));
    assert.doesNotMatch(h.label, /Chrome or Edge/);
  }
});

test('Android and ChromeOS are not treated as Linux', () => {
  for (const ua of [UA.chromeAndroid, UA.chromeOS]) assert.doesNotMatch(help(ua).title, /Linux/);
});

test('an insecure page comes first, whatever the browser', () => {
  for (const ua of [UA.chromeLinux, UA.chromeWin, UA.firefoxLinux])
    assert.match(help(ua, { secure: false }).label, /https/);
});

test('Brave, on Linux too: its own setting', () => {
  for (const ua of [UA.chromeWin, UA.chromeLinux])
    assert.ok(help(ua, { brave: true }).steps[0].includes('brave://flags/#brave-web-bluetooth-api'));
});

test('other Chromium browsers: switched off', () => {
  assert.match(help(UA.chromeWin).title, /off/);
});

test('Firefox and Safari: use Chrome or Edge', () => {
  for (const ua of [UA.firefoxLinux, UA.safari]) assert.match(help(ua).label, /Chrome or Edge/);
});
