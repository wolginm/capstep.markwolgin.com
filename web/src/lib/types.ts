/**
 * Types for the data files the site loads at runtime.
 *
 * `Catalog` mirrors `data/catalog.json` as written by
 * `ingest/capsteps_ingest/build_catalog.py`; `Reference` mirrors one entry of
 * `references/references.yaml`.
 *
 * @references
 *   [TS-TSCONFIG] TypeScript, https://www.typescriptlang.org/tsconfig/
 */

/** What kind of recording an audio file is (see `song_kind` in build_catalog.py). */
export type SongKind = 'song' | 'lirty-dies' | 'radio-show' | 'promo' | 'interview'

/** One archived page or file that a song's details were taken from. */
export interface SourceRef {
  /** Bibliography ID, e.g. `WAYBACK-CAPSTEPS-HOME`. */
  ref: string
  /** Canonical page URL without scheme, e.g. `capsteps.com/`. */
  page: string
  /** Wayback capture timestamp, `YYYYMMDDhhmmss`. */
  timestamp: string
  /** Wayback URL of that capture. */
  url: string
}

/** One playable recording in the catalog. */
export interface Song {
  id: string
  base_slug: string
  title: string
  /** `archive`: printed on capsteps.com; `filename`: made from the file name (flagged on the site). */
  title_source: 'archive' | 'filename'
  alternate_titles: string[]
  kind: SongKind
  original_song: string
  album: { title: string; year: string } | null
  /** ISO date (`YYYY-MM-DD`) of the "Week of ..." the song was featured, or `""`. */
  featured_week: string
  first_seen_year: number
  /** Excerpt (at most 300 characters) of the archived blurb, or `""`. */
  description: string
  audio: {
    original_url: string
    mimetype: string
    best_timestamp: string
    all_timestamps: string[]
    wayback_raw_url: string
    wayback_view_url: string
  }
  copyright: { notice: string; holder: string; source_url: string }
  sources: SourceRef[]
  sightings: number
}

/** The whole of `data/catalog.json`. */
export interface Catalog {
  generated: string
  description: string
  takedown_email: string
  references: string[]
  counts: { songs: number; legacy_only_excluded: number; unarchived_excluded: number }
  songs: Song[]
}

/** One bibliography entry (`references/references.yaml`). */
export interface Reference {
  id: string
  title: string
  url: string
  accessed: string
  author?: string
  publisher?: string
  note?: string
}
