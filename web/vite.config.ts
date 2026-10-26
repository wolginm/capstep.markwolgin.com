/**
 * Vite and Vitest configuration.
 *
 * `base: './'` makes every asset URL relative, so the same build works at a domain
 * root (self-hosted) or under a project sub-path (GitHub Pages).
 *
 * @references
 *   [VITE-CONFIG] base, https://vite.dev/config/shared-options.html
 *   [VITE-STATIC-DEPLOY] https://vite.dev/guide/static-deploy.html
 *   [VITEST-CONFIG] test.environment, setupFiles, include, https://vitest.dev/config/
 */

import react from '@vitejs/plugin-react'
import { defineConfig } from 'vitest/config'

export default defineConfig({
  base: './',
  plugins: [react()],
  test: {
    environment: 'jsdom',
    setupFiles: ['./src/test/setup.ts'],
    include: ['src/**/*.test.{ts,tsx}', 'scripts/**/*.test.ts'],
  },
})
