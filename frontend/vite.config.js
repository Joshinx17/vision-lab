import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import { cpSync, mkdirSync } from 'node:fs';

export default defineConfig({
  plugins: [react(), {
    name: 'local-mediapipe-assets',
    closeBundle() {
      mkdirSync('dist/mediapipe', { recursive: true });
      cpSync('node_modules/@mediapipe/hands', 'dist/mediapipe', { recursive: true });
    },
  }],
});
