import js from '@eslint/js';
import globals from 'globals';
export default [
  { ignores: ['dist/**', 'public/**'] },
  js.configs.recommended,
  { files: ['src/**/*.{js,jsx}'], languageOptions: { globals: globals.browser, parserOptions: { ecmaFeatures: { jsx: true } } }, rules: { 'no-unused-vars': ['error', { varsIgnorePattern: '^[A-Z_]' }] } },
  { files: ['vite.config.js'], languageOptions: { globals: globals.node } },
];
