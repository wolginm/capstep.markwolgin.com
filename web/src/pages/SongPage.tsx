/**
 * Song detail page: metadata, player streaming from the Wayback Machine, capture
 * dates, the copyright notice exactly as archived, sources, and a takedown link.
 *
 * @references
 *   [MDN-AUDIO] <audio controls preload="none">,
 *     https://developer.mozilla.org/en-US/docs/Web/HTML/Reference/Elements/audio
 *   [IA-WAYBACK-URL] `id_` raw capture for playback, plain view URL for links,
 *     https://en.wikipedia.org/wiki/Help:Using_the_Wayback_Machine
 *   [REACT-ROUTER-ROUTING] useParams, Link, https://reactrouter.com/start/declarative/routing
 */

import { Link, useParams } from 'react-router'
import { Loading } from '../components/Loading'
import { useSiteData } from '../lib/data'
import { albumLabel, formatTimestamp, kindLabel, takedownMailto, waybackViewUrl } from '../lib/format'
import type { Song } from '../lib/types'

/**
 * The `/song/:id` route.
 *
 * @references
 *   [REACT-ROUTER-ROUTING] useParams, https://reactrouter.com/start/declarative/routing
 */
export function SongPage() {
  const { id = '' } = useParams()
  const { catalog } = useSiteData()
  return (
    <Loading data={catalog}>
      {(value) => {
        const song = value.songs.find((s) => s.id === id)
        return song ? <SongDetail song={song} /> : <SongNotFound id={id} />
      }}
    </Loading>
  )
}

/**
 * Message for an unknown song id.
 *
 * @references
 *   None.
 */
function SongNotFound({ id }: { id: string }) {
  return (
    <>
      <h1>Recording not found</h1>
      <p>
        There is no recording with the id <code>{id}</code>. <Link to="/">Browse all recordings</Link>.
      </p>
    </>
  )
}

/**
 * Everything known about one recording.
 *
 * @references
 *   [MDN-AUDIO] https://developer.mozilla.org/en-US/docs/Web/HTML/Reference/Elements/audio
 *   [WCAG-22] 1.1.1 / 4.1.2: the player is labelled with the song title, https://www.w3.org/TR/WCAG22/
 */
export function SongDetail({ song }: { song: Song }) {
  const { audio } = song
  return (
    <article className="song">
      <p className="breadcrumb">
        <Link to="/">← All recordings</Link>
      </p>
      <h1>{song.title}</h1>
      {song.title_source === 'filename' && (
        <p className="note">
          The archived site does not name this recording; this title was made from its file name (
          <code>{audio.original_url.split('/').pop()}</code>).
        </p>
      )}

      <dl className="facts">
        <dt>Kind</dt>
        <dd>{kindLabel(song.kind)}</dd>
        {song.original_song && (
          <>
            <dt>Parody of</dt>
            <dd>{song.original_song}</dd>
          </>
        )}
        {song.album && (
          <>
            <dt>Album</dt>
            <dd>{albumLabel(song)}</dd>
          </>
        )}
        {song.featured_week && (
          <>
            <dt>Featured on capsteps.com</dt>
            <dd>Week of {song.featured_week}</dd>
          </>
        )}
        <dt>First archived</dt>
        <dd>{song.first_seen_year}</dd>
        {song.alternate_titles.length > 0 && (
          <>
            <dt>Also titled</dt>
            <dd>{song.alternate_titles.join('; ')}</dd>
          </>
        )}
      </dl>

      {song.description && (
        <figure className="blurb">
          <blockquote cite={song.sources[0]?.url}>
            <p>{song.description}</p>
          </blockquote>
          <figcaption>
            Excerpt from capsteps.com, as archived by the Wayback Machine
            {song.sources[0] && (
              <>
                {' '}
                (<a href={song.sources[0].url}>capture of {formatTimestamp(song.sources[0].timestamp)}</a>)
              </>
            )}
            .
          </figcaption>
        </figure>
      )}

      <section aria-labelledby="listen">
        <h2 id="listen">Listen</h2>
        <audio controls preload="none" src={audio.wayback_raw_url} aria-label={`Play “${song.title}”`}>
          Your browser cannot play audio here. <a href={audio.wayback_view_url}>Open the recording in the Wayback Machine</a>.
        </audio>
        <p className="small">
          Streams from the Internet Archive (capture of {formatTimestamp(audio.best_timestamp)}). Nothing is downloaded
          until you press play. <a href={audio.wayback_view_url}>Open in the Wayback Machine</a>.
        </p>
      </section>

      <section aria-labelledby="copyright">
        <h2 id="copyright">Copyright</h2>
        {song.copyright.notice && (
          <blockquote className="notice" cite={song.copyright.source_url || undefined}>
            <p>{song.copyright.notice}</p>
          </blockquote>
        )}
        {song.copyright.notice && song.copyright.source_url && (
          <p className="small">
            Notice quoted exactly as it appeared on the{' '}
            <a href={song.copyright.source_url}>archived capsteps.com page</a>.
          </p>
        )}
        <p className="small">
          This site does not host or copy this recording; it links to the Internet Archive’s copy.{' '}
          <a href={takedownMailto(song.title)}>Report a copyright issue with this recording</a>.
        </p>
      </section>

      <section aria-labelledby="captures">
        <h2 id="captures">Archived copies of the audio file</h2>
        <ul className="captures">
          {audio.all_timestamps.map((ts) => (
            <li key={ts}>
              <a href={waybackViewUrl(ts, audio.original_url)}>{formatTimestamp(ts)}</a>
            </li>
          ))}
        </ul>
      </section>

      <section aria-labelledby="sources">
        <h2 id="sources">Sources</h2>
        <ul>
          {song.sources.map((source) => (
            <li key={`${source.ref}-${source.timestamp}-${source.page}`}>
              <a href={source.url}>
                {source.page}, captured {formatTimestamp(source.timestamp)}
              </a>{' '}
              <Link to={`/bibliography?ref=${encodeURIComponent(source.ref)}`}>[{source.ref}]</Link>
            </li>
          ))}
        </ul>
      </section>
    </article>
  )
}
