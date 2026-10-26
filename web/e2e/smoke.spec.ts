/**
 * Smoke test of the production build with the real catalog: browse, search, open a
 * song, and check the footer and player. Requests to the Internet Archive are
 * blocked, so tests never load archived audio.
 *
 * @references
 *   [PLAYWRIGHT-CONFIG] https://playwright.dev/docs/test-configuration
 *   [MDN-AUDIO] preload="none", https://developer.mozilla.org/en-US/docs/Web/HTML/Reference/Elements/audio
 */

import { expect, test } from '@playwright/test'

const LLM_FOOTER = 'Built primarily with an AI model (LLM); a human developer drove every decision.'

test.beforeEach(async ({ page }) => {
  await page.route('https://web.archive.org/**', (route) => route.abort())
})

test('browse, search and open a song', async ({ page }) => {
  await page.goto('./')
  await expect(page.getByRole('heading', { level: 1 })).toHaveText('Browse the recordings')
  await expect(page.getByRole('status')).toHaveText(/^\d{3} recordings$/)
  await expect(page.getByRole('contentinfo')).toContainText(LLM_FOOTER)

  await page.getByLabel('Search').fill('no-reiga')
  await expect(page.getByRole('status')).toHaveText(/^1 of \d{3} recordings match$/)
  await page.getByRole('link', { name: 'Yes, We Have No-Reiga' }).click()

  await expect(page).toHaveURL(/#\/song\/noriega$/)
  await expect(page.getByRole('heading', { level: 1 })).toHaveText('Yes, We Have No-Reiga')
  const audio = page.locator('audio')
  await expect(audio).toHaveAttribute('src', /^https:\/\/web\.archive\.org\/web\/\d{14}id_\/.*noriega\.mp3$/)
  await expect(audio).toHaveAttribute('preload', 'none')
  await expect(page.getByText('Do not redistribute.')).toBeVisible()
  await expect(page.getByRole('contentinfo')).toContainText(LLM_FOOTER)
})

test('deep links and every page load from the built site', async ({ page }) => {
  for (const [hash, heading] of [
    ['#/about', 'About'],
    ['#/copyright', 'Copyright & takedown'],
    ['#/bibliography?ref=IA-WAYBACK-URL', 'Bibliography'],
    ['#/ai-disclosure', 'AI Usage Log'],
  ]) {
    await page.goto(`./${hash}`)
    await expect(page.getByRole('heading', { level: 1 })).toHaveText(heading)
    await expect(page.getByRole('contentinfo')).toContainText(LLM_FOOTER)
    if (hash.startsWith('#/bibliography')) await expect(page.locator('#ref-IA-WAYBACK-URL')).toHaveClass('highlight')
  }
})
