import { test, expect } from '@playwright/test';

// One view per course: its normal start, in its normal weather.
const COURSES = [
  { name: 'valley', query: '' },
  { name: 'christmas', query: 'theme=christmas' },
  { name: 'leckhampton', query: 'course=leckhampton' },
];

// Software rendering takes over a minute to composite the page's blurred-glass buttons, so the tests turn the blur off.
const noBlur = () =>
  addEventListener('DOMContentLoaded', () => {
    const style = document.createElement('style');
    style.textContent = '* { backdrop-filter: none !important; }';
    document.head.append(style);
  });

for (const course of COURSES) {
  test(course.name, async ({ page }) => {
    await page.addInitScript(noBlur);
    // ?freeze stops the clock, and stops drawing once the view is complete (window.ride.held).
    await page.goto(`?freeze&${course.query}`);
    await page.waitForFunction(() => window.ride?.held && !document.getElementById('loading'), null, {
      timeout: 5 * 60_000,
    });
    await expect(page).toHaveScreenshot(`${course.name}.png`);
  });
}
