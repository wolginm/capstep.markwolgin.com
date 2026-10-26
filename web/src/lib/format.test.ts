/**
 * Tests for format.ts and config.ts.
 *
 * @references
 *   [VITEST-CONFIG] https://vitest.dev/config/
 *   [RFC-6068] mailto subject encoding, https://www.rfc-editor.org/rfc/rfc6068
 */

import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { describe, expect, it } from 'vitest'
import { TAKEDOWN_EMAIL } from '../config'
import { makeSong } from '../test/fixtures'
import { albumLabel, formatTimestamp, kindLabel, songYear, takedownMailto, waybackViewUrl } from './format'

describe('format', () => {
  it('formats Wayback timestamps as ISO dates', () => {
    expect(formatTimestamp('20210213225452')).toBe('2021-02-13')
    expect(formatTimestamp('2021')).toBe('2021')
  })

  it('builds Wayback view URLs', () => {
    expect(waybackViewUrl('20150522182442', 'https://www.capsteps.com/sounds/noriega.mp3')).toBe(
      'https://web.archive.org/web/20150522182442/https://www.capsteps.com/sounds/noriega.mp3',
    )
  })

  it('pre-fills the required takedown subject, percent-encoded', () => {
    const url = takedownMailto("Bye, Bye, Big Bird & Friends")
    expect(url.startsWith('mailto:wolginmark@gmail.com?subject=')).toBe(true)
    const subject = decodeURIComponent(url.split('subject=')[1])
    expect(subject).toBe('COPYRIGHT TAKEDOWN NOTICE -- Bye, Bye, Big Bird & Friends')
    expect(url).not.toContain('&F') // "&" must be encoded, or it would start a new header field
  })

  it('leaves the subject suffix blank on the general page', () => {
    expect(decodeURIComponent(takedownMailto('').split('subject=')[1])).toBe('COPYRIGHT TAKEDOWN NOTICE -- ')
  })

  it('uses the featured year, else the first-archived year', () => {
    expect(songYear(makeSong({ id: 'a', featured_week: '2007-07-30', first_seen_year: 2015 }))).toBe(2007)
    expect(songYear(makeSong({ id: 'b', first_seen_year: 2015 }))).toBe(2015)
  })

  it('labels albums and kinds', () => {
    expect(albumLabel(makeSong({ id: 'a', album: { title: 'Obama Mia!', year: '2009' } }))).toBe('Obama Mia! (2009)')
    expect(albumLabel(makeSong({ id: 'b', album: { title: 'We Arm The World', year: '' } }))).toBe('We Arm The World')
    expect(albumLabel(makeSong({ id: 'c' }))).toBe('')
    expect(kindLabel('lirty-dies')).toBe('Lirty Dies')
  })
})

describe('config', () => {
  // Vitest runs from web/, so repository files are resolved from the working directory.
  it('takedown address matches the one recorded in data/catalog.json', () => {
    const catalog = JSON.parse(readFileSync(resolve(process.cwd(), '../data/catalog.json'), 'utf8'))
    expect(TAKEDOWN_EMAIL).toBe(catalog.takedown_email)
  })
})
