/**
 * Playwright smoke-test configuration: build the site, serve it with `vite preview`,
 * and run e2e/ against it in Chromium.
 *
 * @references
 *   [PLAYWRIGHT-CONFIG] https://playwright.dev/docs/test-configuration
 *   [PLAYWRIGHT-WEBSERVER] webServer, https://playwright.dev/docs/test-webserver
 */

import { defineConfig, devices } from '@playwright/test'

const PORT = 4173

export default defineConfig({
  testDir: './e2e',
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 1 : 0,
  reporter: process.env.CI ? 'github' : 'list',
  use: { baseURL: `http://localhost:${PORT}/` },
  projects: [{ name: 'chromium', use: { ...devices['Desktop Chrome'] } }],
  webServer: {
    command: `npm run build && npx vite preview --port ${PORT} --strictPort`,
    url: `http://localhost:${PORT}/`,
    reuseExistingServer: !process.env.CI,
    timeout: 120_000,
  },
})
