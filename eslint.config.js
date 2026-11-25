import js from '@eslint/js';
import globals from 'globals';

export default [
  // assets/ holds generated course data. The script inside index.html is linted once it moves to src/ (phase 2).
  { ignores: ['assets/', 'node_modules/', '_site/'] },
  js.configs.recommended,
  {
    files: ['**/*.js'],
    languageOptions: { ecmaVersion: 2024, sourceType: 'module', globals: { ...globals.browser } },
  },
  {
    files: ['eslint.config.js', 'tests/**/*.js'],
    languageOptions: { globals: { ...globals.node } },
  },
];
