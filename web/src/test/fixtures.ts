/**
 * Small hand-made catalog for component tests, modelled on real entries of
 * `data/catalog.json` (Phase 2 output).
 *
 * @references
 *   [WAYBACK-CAPSTEPS-HOME] source of the modelled entries, https://web.archive.org/web/2006%2A/capsteps.com/
 */

import type { Catalog, Reference, Song } from '../lib/types'

const NOTICE =
  'Recordings and lyrics Copyright © by Newport and Eaton. This work includes parodies of the original songs. ' +
  'These audio files are provided for individual listening only. Do not redistribute.'

/**
 * Build a song with sensible defaults; override any field.
 *
 * @references
 *   None.
 */
export function makeSong(overrides: Partial<Song> & { id: string }): Song {
  const { id } = overrides
  return {
    base_slug: id.split('-')[0],
    title: id,
    title_source: 'archive',
    alternate_titles: [],
    kind: 'song',
    original_song: '',
    album: null,
    featured_week: '',
    first_seen_year: 2010,
    description: '',
    audio: {
      original_url: `https://www.capsteps.com/sounds/${id}.mp3`,
      mimetype: 'audio/mpeg',
      best_timestamp: '20210213225452',
      all_timestamps: ['20150522182442', '20210213225452'],
      wayback_raw_url: `https://web.archive.org/web/20210213225452id_/https://www.capsteps.com/sounds/${id}.mp3`,
      wayback_view_url: `https://web.archive.org/web/20210213225452/https://www.capsteps.com/sounds/${id}.mp3`,
    },
    copyright: { notice: NOTICE, holder: 'Newport and Eaton', source_url: 'https://web.archive.org/web/20170610094622/http://www.capsteps.com/' },
    sources: [
      {
        ref: 'WAYBACK-CAPSTEPS-HOME',
        page: 'capsteps.com/',
        timestamp: '20170610094622',
        url: 'https://web.archive.org/web/20170610094622/http://www.capsteps.com/',
      },
    ],
    sightings: 1,
    ...overrides,
  }
}

export const SONGS: Song[] = [
  makeSong({
    id: 'noriega',
    title: 'Yes, We Have No-Reiga',
    alternate_titles: ['Yes, We Have No-Riega'],
    original_song: 'Yes, We Have No Bananas',
    album: { title: 'Georgie On My Mind', year: '1990' },
    featured_week: '2007-07-30',
    description: 'IMAGINE a world where President Bush invades a country, restores democracy …',
  }),
  makeSong({
    id: 'bork-supremes',
    title: 'The Supremes',
    original_song: 'Stop! In the Name of Love',
    album: { title: "Workin' 9 To 10", year: '1987' },
    featured_week: '2013-01-07',
  }),
  makeSong({ id: 'lirty-1012', title: 'Lirty Dies: Midterm Medley', kind: 'lirty-dies', first_seen_year: 2011 }),
  makeSong({ id: 'meese-pieces', title: 'Meese Pieces', title_source: 'filename', first_seen_year: 2019 }),
]

export const CATALOG: Catalog = {
  generated: '2026-10-25',
  description: 'test catalog',
  takedown_email: 'wolginmark@gmail.com',
  references: ['WAYBACK-CAPSTEPS-HOME'],
  counts: { songs: SONGS.length, legacy_only_excluded: 72, unarchived_excluded: 94 },
  songs: SONGS,
}

export const REFERENCES: Reference[] = [
  { id: 'WIKI-CAPSTEPS', title: 'Capitol Steps', url: 'https://en.wikipedia.org/wiki/Capitol_Steps', accessed: '2026-10-25' },
  {
    id: 'WAYBACK-CAPSTEPS-HOME',
    title: 'Archived capsteps.com homepage captures',
    url: 'https://web.archive.org/web/*/capsteps.com/',
    accessed: '2026-10-25',
    author: 'Internet Archive',
  },
]

export const AI_USAGE = '# AI Usage Log\n\n| | |\n|---|---|\n| Model | Claude Opus 5.5 (`claude-opus-5-5`) |\n'
