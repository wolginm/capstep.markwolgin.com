/**
 * Small formatting helpers: Wayback timestamps, capture URLs, takedown mailto links.
 *
 * @references
 *   [IA-WAYBACK-URL] Wayback Machine URL formats, https://en.wikipedia.org/wiki/Help:Using_the_Wayback_Machine
 *   [RFC-6068] The 'mailto' URI Scheme, https://www.rfc-editor.org/rfc/rfc6068
 */

import { TAKEDOWN_EMAIL, TAKEDOWN_SUBJECT_PREFIX } from '../config'
import type { Song, SongKind } from './types'

/**
 * Format a Wayback timestamp (`YYYYMMDDhhmmss`) as an ISO date, e.g. `2021-02-13`.
 *
 * @param timestamp - 14-digit Wayback timestamp (shorter prefixes are allowed).
 * @returns `YYYY-MM-DD`, `YYYY-MM` or `YYYY`, depending on the digits given.
 *
 * @references
 *   [IA-CDX-API] timestamp field format, https://github.com/internetarchive/wayback/tree/master/wayback-cdx-server
 */
export function formatTimestamp(timestamp: string): string {
  const parts = [timestamp.slice(0, 4), timestamp.slice(4, 6), timestamp.slice(6, 8)]
  return parts.filter((p) => p.length > 0).join('-')
}

/**
 * Wayback "view" URL (with the archive's toolbar) for one capture of a file.
 *
 * @param timestamp - Capture timestamp.
 * @param originalUrl - The URL as it was archived.
 *
 * @references
 *   [IA-WAYBACK-URL] `/web/<timestamp>/<url>`, https://en.wikipedia.org/wiki/Help:Using_the_Wayback_Machine
 */
export function waybackViewUrl(timestamp: string, originalUrl: string): string {
  return `https://web.archive.org/web/${timestamp}/${originalUrl}`
}

/**
 * Build a `mailto:` link for a takedown request with the required subject line.
 *
 * @param songTitle - Title to append to the subject; `""` leaves the suffix for the
 *   sender to complete (general Copyright page, plan §6).
 * @returns e.g. `mailto:wolginmark@gmail.com?subject=COPYRIGHT%20TAKEDOWN%20NOTICE%20--%20Amazing%20Race`
 *
 * @references
 *   [RFC-6068] `subject` header field, percent-encoded, https://www.rfc-editor.org/rfc/rfc6068
 *   [MDN-ENCODEURICOMPONENT] https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Global_Objects/encodeURIComponent
 */
export function takedownMailto(songTitle: string): string {
  return `mailto:${TAKEDOWN_EMAIL}?subject=${encodeURIComponent(TAKEDOWN_SUBJECT_PREFIX + songTitle)}`
}

const KIND_LABELS: Record<SongKind, string> = {
  song: 'Song',
  'lirty-dies': 'Lirty Dies',
  'radio-show': 'Radio show',
  promo: 'Promo',
  interview: 'Interview',
}

/**
 * Human-readable label for a recording kind.
 *
 * @references
 *   None.
 */
export function kindLabel(kind: SongKind): string {
  return KIND_LABELS[kind]
}

/**
 * The year a song is listed under: the year it was featured on capsteps.com, or,
 * if the archive has no "Week of" date, the year its audio file was first archived.
 *
 * @references
 *   None.
 */
export function songYear(song: Song): number {
  return song.featured_week ? Number(song.featured_week.slice(0, 4)) : song.first_seen_year
}

/**
 * Album name with its year, e.g. `Obama Mia! (2009)`, or `""` when there is no album.
 *
 * @references
 *   None.
 */
export function albumLabel(song: Song): string {
  if (!song.album) return ''
  return song.album.year ? `${song.album.title} (${song.album.year})` : song.album.title
}
