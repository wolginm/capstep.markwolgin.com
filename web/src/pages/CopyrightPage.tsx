/**
 * Copyright & takedown policy (plan/PLAN.md §6).
 *
 * @references
 *   [RFC-6068] mailto with a pre-filled subject, https://www.rfc-editor.org/rfc/rfc6068
 *   [IA-WAYBACK-URL] links to archived copies, https://en.wikipedia.org/wiki/Help:Using_the_Wayback_Machine
 */

import { TAKEDOWN_EMAIL, TAKEDOWN_SUBJECT_PREFIX } from '../config'
import { takedownMailto } from '../lib/format'

/**
 * The `/copyright` route.
 *
 * @references
 *   [RFC-6068] https://www.rfc-editor.org/rfc/rfc6068
 */
export function CopyrightPage() {
  return (
    <>
      <h1>Copyright &amp; takedown</h1>

      <h2>Rights</h2>
      <p>
        The recordings and lyrics belong to their copyright holders. The archived capsteps.com pages credited them to
        Bill Strauss and Elaina Newport, later to Strauss, Newport and Mark Eaton, and later to Newport and Eaton; the
        notice shown on each song page is quoted exactly as it appeared on the archived page, including the original
        instruction that the files were “provided for individual listening only. Do not redistribute.”
      </p>

      <h2>How this site respects that</h2>
      <ul>
        <li>
          No audio, lyrics or artwork is copied into this project or served from its host. The player streams each file
          directly from the Internet Archive’s Wayback Machine, and nothing is requested until you press play.
        </li>
        <li>Descriptions are short excerpts, each linked to the archived page it was quoted from.</li>
        <li>This is an unofficial, non-commercial preservation index, not affiliated with the Capitol Steps.</li>
      </ul>

      <h2>Takedown requests</h2>
      <p>
        If you hold rights in any listed recording and want it removed from this index, email{' '}
        <a href={takedownMailto('')}>{TAKEDOWN_EMAIL}</a> with the subject line{' '}
        <code>{TAKEDOWN_SUBJECT_PREFIX}</code> followed by the song title. Each song page has a link that fills this in
        for you. Please identify the recording and your relationship to the rights.
      </p>
      <p className="small">
        Removing a listing here does not remove the Internet Archive’s copy; for that, contact the Internet Archive
        directly.
      </p>
    </>
  )
}
