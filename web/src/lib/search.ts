/**
 * Filtering and sorting for the Browse page.
 *
 * @references
 *   [MDN-INTL-COLLATOR] Intl.Collator (sensitivity "base"),
 *     https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Global_Objects/Intl/Collator
 */

import { songYear } from './format'
import type { Song, SongKind } from './types'

export type SortKey = 'title' | 'year' | 'album'

export interface SongQuery {
  /** Free text matched against title, alternate titles, parodied song, album and description. */
  text: string
  kind: SongKind | ''
  album: string
  year: number | null
  sort: SortKey
}

export const EMPTY_QUERY: SongQuery = { text: '', kind: '', album: '', year: null, sort: 'title' }

const collator = new Intl.Collator('en', { sensitivity: 'base', numeric: true })

/**
 * Fold text for matching: lower case, accents and punctuation removed.
 *
 * @references
 *   [MDN-INTL-COLLATOR] (same folding goal as sensitivity "base"),
 *     https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Global_Objects/Intl/Collator
 */
export function fold(text: string): string {
  return text
    .normalize('NFKD')
    .replace(/\p{M}/gu, '')
    .toLowerCase()
    .replace(/[^\p{L}\p{N}]+/gu, ' ')
    .trim()
}

/**
 * Sort key for titles: ignores a leading article and quotes ("The Supremes" sorts under S).
 *
 * @references
 *   None.
 */
function titleSortKey(title: string): string {
  return title.replace(/^[\s"'“‘(]*(?:the|a|an)\s+/i, '').replace(/^[\s"'“‘(]+/, '')
}

/**
 * True if every word of the query text appears in one of the song's text fields.
 *
 * @references
 *   None.
 */
function matchesText(song: Song, words: string[]): boolean {
  if (words.length === 0) return true
  const haystack = fold(
    [song.title, ...song.alternate_titles, song.original_song, song.album?.title ?? '', song.description].join(' '),
  )
  return words.every((word) => haystack.includes(word))
}

/**
 * Apply a Browse-page query: filter, then sort.
 *
 * @param songs - All catalog songs.
 * @param query - Search text, filters and sort key.
 * @returns A new, sorted array; the input is not modified.
 *
 * @references
 *   [MDN-INTL-COLLATOR] locale-aware compare,
 *     https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Global_Objects/Intl/Collator
 */
export function querySongs(songs: Song[], query: SongQuery): Song[] {
  const words = fold(query.text).split(' ').filter(Boolean)
  const byTitle = (a: Song, b: Song) => collator.compare(titleSortKey(a.title), titleSortKey(b.title))
  const compare: Record<SortKey, (a: Song, b: Song) => number> = {
    title: byTitle,
    year: (a, b) => songYear(a) - songYear(b) || byTitle(a, b),
    album: (a, b) => {
      if (!a.album !== !b.album) return a.album ? -1 : 1 // songs with no album last
      return collator.compare(a.album?.title ?? '', b.album?.title ?? '') || byTitle(a, b)
    },
  }
  return songs
    .filter(
      (song) =>
        matchesText(song, words) &&
        (!query.kind || song.kind === query.kind) &&
        (!query.album || song.album?.title === query.album) &&
        (query.year === null || songYear(song) === query.year),
    )
    .sort(compare[query.sort])
}

/**
 * Distinct values for the filter menus.
 *
 * @returns Album titles (sorted) and years (ascending).
 *
 * @references
 *   [MDN-INTL-COLLATOR] https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Global_Objects/Intl/Collator
 */
export function filterOptions(songs: Song[]): { albums: string[]; years: number[] } {
  const albums = [...new Set(songs.flatMap((s) => (s.album ? [s.album.title] : [])))].sort(collator.compare)
  const years = [...new Set(songs.map(songYear))].sort((a, b) => a - b)
  return { albums, years }
}
