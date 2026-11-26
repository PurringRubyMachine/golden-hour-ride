// Why Web Bluetooth is missing, and what the rider can do about it. Pure: no DOM, so it is unit-tested.

const FLAG = 'chrome://flags/#enable-experimental-web-platform-features';

// bluetooth: navigator.bluetooth; secure: window.isSecureContext; userAgent: navigator.userAgent;
// brave: whether navigator.brave exists (Brave hides itself in the user agent).
// Returns null when Web Bluetooth is there, otherwise { label, title, steps } for the likeliest cause.
export function bluetoothHelp({ bluetooth, secure, userAgent = '', brave = false }) {
  if (bluetooth) return null;
  const ua = userAgent;
  const chromium = /(Chrome|Chromium|CriOS|Edg)\//.test(ua);
  if (!secure)
    return {
      label: 'Trainer: needs https',
      title: 'Bluetooth only works on a secure page',
      steps: [
        'Browsers only allow Bluetooth on pages opened over https, or from this computer as localhost.',
        'Open the ride from its https address, or run it on the computer you ride with and open http://localhost:8791/.',
      ],
    };
  if (brave)
    return {
      label: 'Trainer: turn on Bluetooth',
      title: 'Brave keeps Bluetooth off',
      steps: ['Open brave://flags/#brave-web-bluetooth-api in a new tab, set it to Enabled, and relaunch Brave.'],
    };
  if (chromium && /\bLinux\b/.test(ua) && !/\b(Android|CrOS)\b/.test(ua))
    return {
      label: 'Trainer: turn on Bluetooth',
      title: 'Chrome on Linux keeps Bluetooth off',
      steps: [
        'Chrome on Linux has Web Bluetooth, but switched off until you turn it on.',
        `Open ${FLAG} in a new tab, set “Experimental Web Platform features” to Enabled, and relaunch Chrome.`,
        'Also check that Bluetooth is on in the system settings.',
      ],
    };
  if (chromium)
    return {
      label: 'Trainer: turn on Bluetooth',
      title: 'Bluetooth is off in this browser',
      steps: [
        'This browser has Web Bluetooth switched off.',
        `Try ${FLAG} (set it to Enabled and relaunch), or use Google Chrome or Microsoft Edge.`,
      ],
    };
  return {
    label: 'Trainer: needs Chrome or Edge',
    title: 'This browser has no Bluetooth for web pages',
    steps: [
      'Firefox and Safari can’t talk to Bluetooth devices from a web page.',
      'Open the ride in Google Chrome or Microsoft Edge (on Windows, macOS, ChromeOS, Android or Linux).',
    ],
  };
}
