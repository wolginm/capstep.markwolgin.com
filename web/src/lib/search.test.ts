/**
 * Tests for search.ts.
 *
 * @references
 *   [VITEST-CONFIG] https://vitest.dev/config/
 */

import { describe, expect, it } from 'vitest'
import { SONGS, makeSong } from '../test/fixtures'
import { EMPTY_QUERY, filterOptions, fold, querySongs } from './search'

const titles = (songs: { title: string }[]) => songs.map((s) => s.title)

describe('search', () => {
  it('folds case, accents and punctuation', () => {
    expect(fold('Café—NO-REIGA!')).toBe('cafe no reiga')
  })

  it('sorts by title ignoring a leading article', () => {
    expect(titles(querySongs(SONGS, EMPTY_QUERY))).toEqual([
      'Lirty Dies: Midterm Medley',
      'Meese Pieces',
      'The Supremes',
      'Yes, We Have No-Reiga',
    ])
  })

  it('matches every word across title, alternates, parodied song, album and description', () => {
    expect(titles(querySongs(SONGS, { ...EMPTY_QUERY, text: 'bananas' }))).toEqual(['Yes, We Have No-Reiga'])
    expect(titles(querySongs(SONGS, { ...EMPTY_QUERY, text: 'no riega' }))).toEqual(['Yes, We Have No-Reiga'])
    expect(titles(querySongs(SONGS, { ...EMPTY_QUERY, text: 'georgie imagine' }))).toEqual(['Yes, We Have No-Reiga'])
    expect(querySongs(SONGS, { ...EMPTY_QUERY, text: 'bananas supremes' })).toEqual([])
  })

  it('filters by kind, album and year', () => {
    expect(titles(querySongs(SONGS, { ...EMPTY_QUERY, kind: 'lirty-dies' }))).toEqual(['Lirty Dies: Midterm Medley'])
    expect(titles(querySongs(SONGS, { ...EMPTY_QUERY, album: "Workin' 9 To 10" }))).toEqual(['The Supremes'])
    expect(titles(querySongs(SONGS, { ...EMPTY_QUERY, year: 2007 }))).toEqual(['Yes, We Have No-Reiga'])
  })

  it('sorts by year, then by album with album-less songs last', () => {
    expect(titles(querySongs(SONGS, { ...EMPTY_QUERY, sort: 'year' }))).toEqual([
      'Yes, We Have No-Reiga',
      'Lirty Dies: Midterm Medley',
      'The Supremes',
      'Meese Pieces',
    ])
    expect(titles(querySongs(SONGS, { ...EMPTY_QUERY, sort: 'album' })).slice(0, 2)).toEqual([
      'Yes, We Have No-Reiga',
      'The Supremes',
    ])
  })

  it('does not modify its input', () => {
    const songs = [makeSong({ id: 'b', title: 'B' }), makeSong({ id: 'a', title: 'A' })]
    querySongs(songs, EMPTY_QUERY)
    expect(titles(songs)).toEqual(['B', 'A'])
  })

  it('lists distinct albums and years for the filter menus', () => {
    expect(filterOptions(SONGS)).toEqual({
      albums: ['Georgie On My Mind', "Workin' 9 To 10"],
      years: [2007, 2011, 2013, 2019],
    })
  })
})
