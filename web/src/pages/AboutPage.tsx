/**
 * About: who the Capitol Steps were (cited) and what this site is and is not.
 *
 * @references
 *   [WIKI-CAPSTEPS] Wikipedia, "Capitol Steps", https://en.wikipedia.org/wiki/Capitol_Steps
 *   [WAYBACK-CAPSTEPS-SOUNDS] archived audio files,
 *     https://web.archive.org/cdx/search/cdx?url=capsteps.com&matchType=domain&filter=mimetype:audio.*
 */

import { Link } from 'react-router'
import { Loading } from '../components/Loading'
import { useSiteData } from '../lib/data'

/**
 * The `/about` route.
 *
 * @references
 *   [WIKI-CAPSTEPS] https://en.wikipedia.org/wiki/Capitol_Steps
 */
export function AboutPage() {
  const { catalog } = useSiteData()
  return (
    <>
      <h1>About</h1>

      <h2>The Capitol Steps</h2>
      <p>
        The Capitol Steps were an American political-satire troupe that performed from 1981 to 2020. Most of their
        material parodied well-known songs and poems, rewritten about the politics of the day. From the late 1980s they
        also performed “Lirty Dies”, spoonerism routines about recent scandals. Originally made up of congressional
        staffers, the troupe later consisted mainly of professional actors and singers. They released more than 40
        albums, appeared on PBS and public radio, and announced on January 13, 2021 that they were shutting down after 39
        years.{' '}
        <Link to="/bibliography?ref=WIKI-CAPSTEPS" aria-label="Source: Wikipedia, Capitol Steps (bibliography)">
          [WIKI-CAPSTEPS]
        </Link>
      </p>

      <h2>What this site is</h2>
      <ul>
        <li>
          An unofficial, non-commercial index of the recordings the Capitol Steps once offered on capsteps.com, as
          preserved by the Internet Archive’s Wayback Machine.
        </li>
        <li>
          Titles, parodied songs, albums, dates and short descriptions were extracted from archived capsteps.com pages.
          Every song page links to the archived pages its details came from.
        </li>
        <li>Built primarily with an AI model, with a human developer making every decision (see the <Link to="/ai-disclosure">AI disclosure</Link>).</li>
      </ul>

      <h2>What this site is not</h2>
      <ul>
        <li>It is not affiliated with or endorsed by the Capitol Steps or the Internet Archive.</li>
        <li>
          It does not host, copy or re-distribute any recording. The player streams each file directly from the Wayback
          Machine. See <Link to="/copyright">Copyright &amp; takedown</Link>.
        </li>
        <li>It is not complete: only files the Wayback Machine captured can be listed.</li>
      </ul>

      <Loading data={catalog}>
        {(value) => (
          <>
            <h2>Coverage</h2>
            <p>
              The index lists {value.counts.songs} playable MP3 recordings. Another {value.counts.legacy_only_excluded}{' '}
              recordings survive only in older RealAudio or Sun audio formats and{' '}
              {value.counts.unarchived_excluded} were linked from the site but never successfully archived; these are
              not listed. Catalog generated {value.generated}.
            </p>
          </>
        )}
      </Loading>
    </>
  )
}
