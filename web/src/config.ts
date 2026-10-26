/**
 * Site-wide settings. The takedown address lives only here (plan §6), so it can be
 * changed in one place; a unit test checks it matches `data/catalog.json`.
 *
 * @references
 *   None (values decided by the developer, plan/PLAN.md §9 item 5).
 */

/** Where copyright holders send takedown requests. */
export const TAKEDOWN_EMAIL = 'wolginmark@gmail.com'

/** Required subject-line prefix; the song title (or nothing, on the general page) follows. */
export const TAKEDOWN_SUBJECT_PREFIX = 'COPYRIGHT TAKEDOWN NOTICE -- '

export const SITE_TITLE = 'Capitol Steps Audio Archive Index'

/** Wording required by the developer for every page footer (plan §5, Phase 3). */
export const LLM_FOOTER_TEXT =
  'Built primarily with an AI model (LLM); a human developer drove every decision.'
