/**
 * Keep the Browse page's query in the URL (`?q=...&kind=...&album=...&year=...&sort=...`),
 * so a filtered list can be bookmarked or shared.
 *
 * @references
 *   [REACT-ROUTER-ROUTING] useSearchParams, https://reactrouter.com/start/declarative/routing
 */

import { EMPTY_QUERY, type SongQuery, type SortKey } from './search'
import type { SongKind } from './types'

export const KINDS: SongKind[] = ['song', 'lirty-dies', 'radio-show', 'promo', 'interview']

export const SORTS: { key: SortKey; label: string }[] = [
  { key: 'title', label: 'Title' },
  { key: 'year', label: 'Year' },
  { key: 'album', label: 'Album' },
]

/**
 * Read a {@link SongQuery} from URL search parameters, ignoring unknown values.
 *
 * @references
 *   [REACT-ROUTER-ROUTING] useSearchParams, https://reactrouter.com/start/declarative/routing
 */
export function queryFromParams(params: URLSearchParams): SongQuery {
  const kind = params.get('kind') ?? ''
  const sort = params.get('sort') ?? ''
  const year = Number(params.get('year'))
  return {
    text: params.get('q') ?? '',
    kind: (KINDS as string[]).includes(kind) ? (kind as SongKind) : '',
    album: params.get('album') ?? '',
    year: Number.isInteger(year) && year > 0 ? year : null,
    sort: SORTS.some((s) => s.key === sort) ? (sort as SortKey) : EMPTY_QUERY.sort,
  }
}

/**
 * Write a {@link SongQuery} back to URL search parameters, omitting defaults.
 *
 * @references
 *   [REACT-ROUTER-ROUTING] useSearchParams, https://reactrouter.com/start/declarative/routing
 */
export function paramsFromQuery(query: SongQuery): URLSearchParams {
  const params = new URLSearchParams()
  if (query.text) params.set('q', query.text)
  if (query.kind) params.set('kind', query.kind)
  if (query.album) params.set('album', query.album)
  if (query.year !== null) params.set('year', String(query.year))
  if (query.sort !== EMPTY_QUERY.sort) params.set('sort', query.sort)
  return params
}
