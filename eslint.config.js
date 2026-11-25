import js from '@eslint/js';
import globals from 'globals';

export default [
  // assets/ holds generated course data.
  { ignores: ['assets/', 'node_modules/', '_site/'] },
  js.configs.recommended,
  {
    files: ['**/*.js'],
    languageOptions: { ecmaVersion: 2024, sourceType: 'module', globals: { ...globals.browser } },
    // An empty catch is how the ride ignores failures it can live with, such as storage being blocked.
    rules: { 'no-empty': ['error', { allowEmptyCatch: true }] },
  },
  {
    files: ['eslint.config.js', 'playwright.config.js', 'tests/**/*.js'],
    languageOptions: { globals: { ...globals.node } },
  },
];
