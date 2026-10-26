/**
 * Tests for scripts/sync-data.ts.
 *
 * @references
 *   [VITEST-CONFIG] https://vitest.dev/config/
 *   [YAML-NPM] https://eemeli.org/yaml/
 */

import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { describe, expect, it } from 'vitest'
import { referencesToJson } from './sync-data.ts'

describe('referencesToJson', () => {
  it('keeps the displayed fields and drops unknown ones', () => {
    const yamlText = [
      'references:',
      '  - id: RFC-6068',
      '    title: "RFC 6068: mailto"',
      '    url: https://www.rfc-editor.org/rfc/rfc6068',
      '    accessed: 2026-10-26',
      '    internal: ignored',
    ].join('\n')
    expect(JSON.parse(referencesToJson(yamlText))).toEqual([
      { id: 'RFC-6068', title: 'RFC 6068: mailto', url: 'https://www.rfc-editor.org/rfc/rfc6068', accessed: '2026-10-26' },
    ])
  })

  it('converts the real registry, with every entry complete', () => {
    const text = readFileSync(resolve(process.cwd(), '../references/references.yaml'), 'utf8') // Vitest runs from web/
    const refs = JSON.parse(referencesToJson(text)) as Record<string, string>[]
    expect(refs.length).toBeGreaterThan(30)
    for (const ref of refs) {
      expect(ref.id).toMatch(/^[A-Z][A-Z0-9]+(?:-[A-Z0-9]+)+$/)
      expect(ref.url).toMatch(/^https?:\/\//)
      expect(ref.accessed).toMatch(/^\d{4}-\d{2}-\d{2}$/)
    }
  })
})
