/**
 * Home / Browse: search, filter and sort every playable recording in the catalog.
 *
 * The query lives in the URL (`?q=...&kind=...&album=...&year=...&sort=...`), so
 * a filtered list can be bookmarked or shared.
 *
 * @references
 *   [REACT-ROUTER-ROUTING] useSearchParams, Link, https://reactrouter.com/start/declarative/routing
 *   [MDN-TABLE] caption and scope for accessible tables,
 *     https://developer.mozilla.org/en-US/docs/Web/HTML/Reference/Elements/table
 *   [WCAG-22] 1.3.1 Info and Relationships (labelled controls), https://www.w3.org/TR/WCAG22/
 */

import { useMemo } from 'react'
import { Link, useSearchParams } from 'react-router'
import { Loading } from '../components/Loading'
import { useSiteData } from '../lib/data'
import { albumLabel, kindLabel, songYear } from '../lib/format'
import { KINDS, SORTS, queryFromParams, paramsFromQuery } from '../lib/query-params'
import { filterOptions, querySongs, type SongQuery, type SortKey } from '../lib/search'
import type { Catalog, SongKind } from '../lib/types'

/**
 * The Browse page route.
 *
 * @references
 *   [REACT-DOCS] useMemo, https://react.dev/reference/react/useMemo
 */
export function BrowsePage() {
  const { catalog } = useSiteData()
  return <Loading data={catalog}>{(value) => <SongBrowser catalog={value} />}</Loading>
}

/**
 * Search form plus results table for a loaded catalog.
 *
 * @references
 *   [REACT-DOCS] useMemo, https://react.dev/reference/react/useMemo
 *   [MDN-TABLE] https://developer.mozilla.org/en-US/docs/Web/HTML/Reference/Elements/table
 */
function SongBrowser({ catalog }: { catalog: Catalog }) {
  const [params, setParams] = useSearchParams()
  const query = queryFromParams(params)
  const options = useMemo(() => filterOptions(catalog.songs), [catalog])
  const results = querySongs(catalog.songs, query) // 686 rows: cheap enough to recompute per keystroke
  const update = (change: Partial<SongQuery>) => setParams(paramsFromQuery({ ...query, ...change }), { replace: true })

  return (
    <>
      <h1>Browse the recordings</h1>
      <p className="lede">
        An index of {catalog.counts.songs} Capitol Steps recordings preserved by the Internet Archive’s Wayback Machine.
        Every recording plays straight from the archive.
      </p>

      <form className="filters" role="search" onSubmit={(e) => e.preventDefault()}>
        <div className="field grow">
          <label htmlFor="q">Search</label>
          <input
            id="q"
            type="search"
            value={query.text}
            placeholder="Title, parodied song, album, or topic"
            onChange={(e) => update({ text: e.target.value })}
          />
        </div>
        <div className="field">
          <label htmlFor="kind">Kind</label>
          <select id="kind" value={query.kind} onChange={(e) => update({ kind: e.target.value as SongKind | '' })}>
            <option value="">All kinds</option>
            {KINDS.map((kind) => (
              <option key={kind} value={kind}>
                {kindLabel(kind)}
              </option>
            ))}
          </select>
        </div>
        <div className="field">
          <label htmlFor="album">Album</label>
          <select id="album" value={query.album} onChange={(e) => update({ album: e.target.value })}>
            <option value="">All albums</option>
            {options.albums.map((album) => (
              <option key={album} value={album}>
                {album}
              </option>
            ))}
          </select>
        </div>
        <div className="field">
          <label htmlFor="year">Year</label>
          <select
            id="year"
            value={query.year ?? ''}
            onChange={(e) => update({ year: e.target.value ? Number(e.target.value) : null })}
          >
            <option value="">All years</option>
            {options.years.map((year) => (
              <option key={year} value={year}>
                {year}
              </option>
            ))}
          </select>
        </div>
        <div className="field">
          <label htmlFor="sort">Sort by</label>
          <select id="sort" value={query.sort} onChange={(e) => update({ sort: e.target.value as SortKey })}>
            {SORTS.map((s) => (
              <option key={s.key} value={s.key}>
                {s.label}
              </option>
            ))}
          </select>
        </div>
      </form>

      <p role="status" className="result-count">
        {results.length === catalog.songs.length
          ? `${results.length} recordings`
          : `${results.length} of ${catalog.songs.length} recordings match`}
      </p>

      {results.length > 0 && (
        <div className="table-wrap">
          <table className="songs">
            <caption className="visually-hidden">Recordings matching the search</caption>
            <thead>
              <tr>
                <th scope="col">Title</th>
                <th scope="col">Parody of</th>
                <th scope="col">Album</th>
                <th scope="col">Year</th>
                <th scope="col">Kind</th>
              </tr>
            </thead>
            <tbody>
              {results.map((song) => (
                <tr key={song.id}>
                  <th scope="row">
                    <Link to={`/song/${encodeURIComponent(song.id)}`}>{song.title}</Link>
                    {song.title_source === 'filename' && (
                      <span className="badge" title="The archive does not name this recording; title made from its file name">
                        file-name title
                      </span>
                    )}
                  </th>
                  <td>{song.original_song}</td>
                  <td>{albumLabel(song)}</td>
                  <td>{songYear(song)}</td>
                  <td>{kindLabel(song.kind)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </>
  )
}
