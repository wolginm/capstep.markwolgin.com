/**
 * Component tests for the pages and the shared layout.
 *
 * @references
 *   [TESTING-LIBRARY-REACT] queries by role and label, https://testing-library.com/docs/react-testing-library/intro/
 *   [JEST-DOM] matchers, https://github.com/testing-library/jest-dom
 */

import { screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it } from 'vitest'
import { LLM_FOOTER_TEXT } from '../config'
import { renderAt } from '../test/render'
import { paramsFromQuery, queryFromParams } from '../lib/query-params'

describe('layout', () => {
  it.each(['/', '/song/noriega', '/about', '/copyright', '/bibliography', '/ai-disclosure', '/nope'])(
    'shows the LLM disclosure footer on %s',
    (path) => {
      renderAt(path)
      const footer = screen.getByRole('contentinfo')
      expect(footer).toHaveTextContent(LLM_FOOTER_TEXT)
      expect(within(footer).getByRole('link', { name: 'How this site was made' })).toHaveAttribute('href', '/ai-disclosure')
    },
  )

  it('has a skip link and labelled navigation', () => {
    renderAt('/')
    expect(screen.getByRole('link', { name: 'Skip to content' })).toBeInTheDocument()
    expect(screen.getByRole('navigation', { name: 'Main' })).toBeInTheDocument()
  })
})

describe('browse page', () => {
  it('lists every recording, flags file-name titles, and filters as you type', async () => {
    renderAt('/')
    expect(screen.getByRole('status')).toHaveTextContent('4 recordings')
    const meese = screen.getByRole('rowheader', { name: /Meese Pieces/ })
    expect(meese).toHaveTextContent('file-name title')

    await userEvent.type(screen.getByLabelText('Search'), 'bananas')
    expect(screen.getByRole('status')).toHaveTextContent('1 of 4 recordings match')
    expect(screen.getByRole('link', { name: 'Yes, We Have No-Reiga' })).toHaveAttribute('href', '/song/noriega')
  })

  it('filters by kind with a labelled select', async () => {
    renderAt('/')
    await userEvent.selectOptions(screen.getByLabelText('Kind'), 'lirty-dies')
    expect(screen.getAllByRole('rowheader').map((r) => r.textContent)).toEqual(['Lirty Dies: Midterm Medley'])
  })

  it('reads its query from the URL and ignores bad values', () => {
    renderAt('/?year=2013')
    expect(screen.getAllByRole('rowheader').map((r) => r.textContent)).toEqual(['The Supremes'])
    const query = queryFromParams(new URLSearchParams('q=x&kind=bogus&year=abc&sort=album'))
    expect(query).toEqual({ text: 'x', kind: '', album: '', year: null, sort: 'album' })
    expect(paramsFromQuery(query).toString()).toBe('q=x&sort=album')
  })
})

describe('song page', () => {
  it('streams from the Wayback raw URL, labelled, with nothing preloaded', () => {
    const { container } = renderAt('/song/noriega')
    expect(screen.getByRole('heading', { level: 1 })).toHaveTextContent('Yes, We Have No-Reiga')
    const audio = container.querySelector('audio')!
    expect(audio).toHaveAttribute(
      'src',
      'https://web.archive.org/web/20210213225452id_/https://www.capsteps.com/sounds/noriega.mp3',
    )
    expect(audio).toHaveAttribute('preload', 'none')
    expect(audio).toHaveAttribute('aria-label', 'Play “Yes, We Have No-Reiga”')
  })

  it('shows the archived copyright notice verbatim and a pre-filled takedown link', () => {
    renderAt('/song/noriega')
    expect(screen.getByText(/These audio files are provided for individual listening only\. Do not redistribute\./)).toBeInTheDocument()
    const takedown = screen.getByRole('link', { name: 'Report a copyright issue with this recording' })
    expect(decodeURIComponent(takedown.getAttribute('href')!)).toBe(
      'mailto:wolginmark@gmail.com?subject=COPYRIGHT TAKEDOWN NOTICE -- Yes, We Have No-Reiga',
    )
  })

  it('lists capture dates, sources with bibliography links, and the facts', () => {
    renderAt('/song/noriega')
    expect(screen.getByRole('link', { name: '2015-05-22' })).toHaveAttribute(
      'href',
      'https://web.archive.org/web/20150522182442/https://www.capsteps.com/sounds/noriega.mp3',
    )
    expect(screen.getByRole('link', { name: '[WAYBACK-CAPSTEPS-HOME]' })).toHaveAttribute(
      'href',
      '/bibliography?ref=WAYBACK-CAPSTEPS-HOME',
    )
    expect(screen.getByText('Yes, We Have No Bananas')).toBeInTheDocument()
    expect(screen.getByText('Georgie On My Mind (1990)')).toBeInTheDocument()
  })

  it('explains file-name titles', () => {
    renderAt('/song/meese-pieces')
    expect(screen.getByText(/this title was made from its file name/)).toBeInTheDocument()
  })

  it('handles unknown ids', () => {
    renderAt('/song/does-not-exist')
    expect(screen.getByRole('heading', { level: 1 })).toHaveTextContent('Recording not found')
  })
})

describe('other pages', () => {
  it('copyright page gives the takedown address with the subject prefix', () => {
    renderAt('/copyright')
    const link = screen.getByRole('link', { name: 'wolginmark@gmail.com' })
    expect(decodeURIComponent(link.getAttribute('href')!)).toBe(
      'mailto:wolginmark@gmail.com?subject=COPYRIGHT TAKEDOWN NOTICE -- ',
    )
  })

  it('bibliography highlights the requested reference', () => {
    renderAt('/bibliography?ref=WAYBACK-CAPSTEPS-HOME')
    const items = screen.getAllByRole('listitem').filter((li) => li.id.startsWith('ref-'))
    expect(items.map((li) => li.id)).toEqual(['ref-WAYBACK-CAPSTEPS-HOME', 'ref-WIKI-CAPSTEPS'])
    expect(items[0]).toHaveClass('highlight')
  })

  it('AI disclosure renders the usage log, including its tables', () => {
    renderAt('/ai-disclosure')
    expect(screen.getByRole('heading', { level: 1 })).toHaveTextContent('AI Usage Log')
    expect(screen.getByRole('table')).toHaveTextContent('Claude Opus 5.5')
  })

  it('about page cites its source and reports coverage', () => {
    renderAt('/about')
    expect(screen.getByRole('link', { name: /Source: Wikipedia/ })).toHaveAttribute('href', '/bibliography?ref=WIKI-CAPSTEPS')
    expect(screen.getByText(/lists 4 playable MP3 recordings/)).toBeInTheDocument()
  })
})
