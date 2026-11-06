/**
 * Tests for scripts/lint-citations.ts.
 *
 * @references
 *   [VITEST-CONFIG] https://vitest.dev/config/
 */

import { describe, expect, it } from 'vitest'
import { lintSource, referencesTag } from './lint-citations.ts'

const KNOWN = new Set(['VITE-CONFIG', 'MDN-FETCH'])
// Built from parts so build_bibliography.py does not see a citation of an unregistered ID.
const UNKNOWN = '[NOT' + '-REAL]'
const HEADER = '/** File. @references None. */\nimport x from "x"\n'

/** Lint a snippet and return `name: message` strings. @references None. */
function lint(text: string, file = 'x.ts'): string[] {
  return lintSource(text, file, KNOWN).map((p) => `${p.name}: ${p.message}`)
}

describe('lint-citations', () => {
  it.each([
    '/** Inline. @references None. */',
    '/** Inline. @references [VITE-CONFIG] */',
    '/**\n * Block.\n *\n * @param a - b\n * @references\n *   [MDN-FETCH] https://example.org\n */',
    '/**\n * Block.\n *\n * @references\n *   None (project rule).\n */',
  ])('accepts a cited or None tag: %s', (doc) => {
    expect(lint(`${HEADER}${doc}\nexport function f() {}\n`)).toEqual([])
  })

  it.each([
    ['', 'missing doc comment with a @references tag'],
    ['/** No tag. */', 'doc comment has no @references tag'],
    ['/** Empty.\n * @references\n * @returns [VITE-CONFIG] elsewhere\n */', '@references must cite an [ID] or say None'],
    [`/** Unknown. @references ${UNKNOWN} */`, `cites ${UNKNOWN}, which is not in references/references.yaml`],
    ['// Line comments are not doc comments. @references None.', 'missing doc comment with a @references tag'],
  ])('rejects %j', (doc, message) => {
    expect(lint(`${HEADER}${doc}\nconst f = () => 1\n`)).toEqual([`f: ${message}`])
  })

  it('requires a file header and does not lend it to the first declaration', () => {
    expect(lint('/** Header only. @references None. */\nexport function f() {}\n')).toEqual([
      'f: missing doc comment with a @references tag',
    ])
    expect(lint('export function f() {}\n')).toEqual([
      '<file>: missing doc comment with a @references tag',
      'f: missing doc comment with a @references tag',
    ])
  })

  it('names nested units and skips anonymous callbacks', () => {
    const text = `${HEADER}
      /** @references None. */
      class C {
        constructor() {}
        m() { [1].map((x) => x); const inner = function () {} }
      }
      it('x', () => {})
    `
    expect(lint(text)).toEqual([
      'C.constructor: missing doc comment with a @references tag',
      'C.m: missing doc comment with a @references tag',
      'C.m.inner: missing doc comment with a @references tag',
    ])
  })

  it('parses TSX', () => {
    expect(lint(`${HEADER}/** @references None. */\nexport function A() { return <p>hi</p> }\n`, 'a.tsx')).toEqual([])
  })

  it('stops the tag at the next tag, but not at an email address', () => {
    expect(referencesTag('/**\n * @references\n *   None\n * @returns x\n */')).toBe('\n  None')
    expect(referencesTag('/** @references None, see wolginmark@gmail.com */')).toContain('gmail.com')
  })
})
