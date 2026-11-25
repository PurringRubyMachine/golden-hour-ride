import { test, expect } from '@playwright/test';

// Fixed spots on each course, in metres along the road. Each spot is captured in each of the course's weathers.
const COURSES = [
  {
    name: 'valley',
    query: '',
    weathers: ['golden', 'mist'],
    views: [
      ['start', 0],
      ['mountains', 1400],
    ],
  },
  {
    name: 'christmas',
    query: 'theme=christmas',
    weathers: ['snow', 'golden'],
    views: [
      ['chalet', 0],
      ['lights', 1400],
    ],
  },
  {
    name: 'leckhampton',
    query: 'course=leckhampton',
    weathers: ['golden', 'mist'],
    views: [
      ['start', 850],
      ['buildings', 1500],
      ['sheep', 2250],
      ['woods', 6750],
      ['stooks', 10500],
    ],
  },
];

// Software rendering takes over a minute to composite the page's blurred-glass buttons, so the tests turn the blur off.
const noBlur = () =>
  addEventListener('DOMContentLoaded', () => {
    const style = document.createElement('style');
    style.textContent = '* { backdrop-filter: none !important; }';
    document.head.append(style);
  });

const FIVE_MINUTES = 5 * 60_000;

for (const course of COURSES) {
  test(course.name, async ({ page }) => {
    await page.addInitScript(noBlur);
    // ?freeze stops the clock, and stops drawing once a view is complete (window.ride.held).
    await page.goto(`?freeze&${course.query}`);
    await page.waitForFunction(() => window.ride?.held && !document.getElementById('loading'), null, {
      timeout: FIVE_MINUTES,
    });
    for (const [view, at] of course.views) {
      for (const weather of course.weathers) {
        await page.evaluate(
          ([at, weather]) => {
            window.ride.weather(weather, true);
            window.ride.go(at);
          },
          [at, weather],
        );
        await page.waitForFunction(() => window.ride.held, null, { timeout: FIVE_MINUTES });
        await expect.soft(page).toHaveScreenshot(`${course.name}-${view}-${weather}.png`);
      }
    }
  });
}
