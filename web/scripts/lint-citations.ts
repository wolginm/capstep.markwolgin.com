/**
 * Fail if any TypeScript file, class or named function lacks a `@references` tag.
 *
 * CLAUDE.md requires every method to list the sources it uses. Here that list is a
 * TSDoc `@references` block tag (declared in `tsdoc.json`). It must cite at least one
 * registered ID (`[VITE-CONFIG]`) or say `None`, and every ID it cites must exist in
 * `references/references.yaml`. The Python twin is `tools/lint_citations.py`.
 *
 * Checked: each file's header comment, classes, class methods, constructors and
 * accessors, function declarations, and functions assigned to a named variable,
 * at any depth. Anonymous callbacks (`items.map((x) => …)`, `it('…', () => …)`)
 * are not methods and are not checked.
 *
 * Run: `node scripts/lint-citations.ts [file ...]` (also part of `npm run lint`).
 *
 * @references
 *   [TS-COMPILER-API] ts.createSourceFile, ts.getLeadingCommentRanges,
 *     https://github.com/microsoft/TypeScript/wiki/Using-the-Compiler-API
 *   [TSDOC-CONFIG] custom block tags, https://tsdoc.org/pages/packages/tsdoc-config/
 *   [YAML-NPM] yaml parse(), https://eemeli.org/yaml/
 *   [NODE-FS] readdir with recursive, readFile, https://nodejs.org/api/fs.html
 *   [NODE-TYPESCRIPT] runs on Node 24 type stripping, https://nodejs.org/api/typescript.html
 */

import { readdir, readFile } from 'node:fs/promises'
import { dirname, join, relative } from 'node:path'
import { fileURLToPath } from 'node:url'
import ts from 'typescript'
import { parse } from 'yaml'

const WEB = join(dirname(fileURLToPath(import.meta.url)), '..')
const ROOT = join(WEB, '..')
const SCAN_DIRS = ['src', 'scripts', 'e2e']
const ROOT_FILES = ['vite.config.ts', 'playwright.config.ts']

/** Same pattern as `CITATION_PATTERN` in tools/build_bibliography.py. */
const CITATION_RE = /\[([A-Z][A-Z0-9]+(?:-[A-Z0-9]+)+)\]/g
const REFERENCES_TAG_RE = /(?:^|\s)@references\b([\s\S]*?)(?=\s@[a-zA-Z]|$)/

/** One lint failure. */
export interface Problem {
  file: string
  line: number
  name: string
  message: string
}

/**
 * The text of a doc comment's `@references` tag, or null if it has none.
 *
 * @param comment - A raw `/** … *\/` comment.
 * @returns The tag's content with comment markup removed, up to the next tag.
 *
 * @references
 *   [MS-TSDOC] block tags run until the next tag, https://tsdoc.org/
 */
export function referencesTag(comment: string): string | null {
  const body = comment
    .replace(/^\/\*\*|\*\/$/g, '')
    .split('\n')
    .map((line) => line.replace(/^\s*\* ?/, ''))
    .join('\n')
  const match = REFERENCES_TAG_RE.exec(body)
  return match ? match[1] : null
}

/**
 * What is wrong with one unit's doc comment (empty if nothing).
 *
 * @param comment - The unit's doc comment, or null if it has none.
 * @param known - Every ID in the reference registry.
 * @returns Human-readable problems.
 *
 * @references
 *   None (project rule, CLAUDE.md and plan/PLAN.md §7).
 */
export function checkComment(comment: string | null, known: ReadonlySet<string>): string[] {
  if (!comment) return ['missing doc comment with a @references tag']
  const tag = referencesTag(comment)
  if (tag === null) return ['doc comment has no @references tag']
  const cited = [...tag.matchAll(CITATION_RE)].map((m) => m[1])
  if (cited.length === 0 && !/^\s*None\b/.test(tag)) return ['@references must cite an [ID] or say None']
  return cited.filter((id) => !known.has(id)).map((id) => `cites [${id}], which is not in references/references.yaml`)
}

/**
 * The last `/** … *\/` comment directly before `pos`, ignoring the file header.
 *
 * @param text - Whole source text.
 * @param pos - A node's full start.
 * @param header - Start of the file header comment, so it is not mistaken for the
 *   first declaration's own doc.
 * @returns The comment text, or null.
 *
 * @references
 *   [TS-COMPILER-API] ts.getLeadingCommentRanges,
 *     https://github.com/microsoft/TypeScript/wiki/Using-the-Compiler-API
 */
function docBefore(text: string, pos: number, header: number | null): string | null {
  const docs = (ts.getLeadingCommentRanges(text, pos) ?? []).filter(
    (r) => r.kind === ts.SyntaxKind.MultiLineCommentTrivia && text.startsWith('/**', r.pos) && r.pos !== header,
  )
  const last = docs.at(-1)
  return last ? text.slice(last.pos, last.end) : null
}

/**
 * A checked unit's name and the node whose leading comments hold its doc, or null
 * if the node is not a unit.
 *
 * @param node - Any AST node.
 * @returns `[name, docNode]` or null.
 *
 * @references
 *   [TS-COMPILER-API] node kinds and type guards,
 *     https://github.com/microsoft/TypeScript/wiki/Using-the-Compiler-API
 */
function unitOf(node: ts.Node): [string, ts.Node] | null {
  if (ts.isFunctionDeclaration(node) || ts.isClassDeclaration(node)) {
    return [node.name?.text ?? 'default', node]
  }
  if (ts.isMethodDeclaration(node) || ts.isGetAccessorDeclaration(node) || ts.isSetAccessorDeclaration(node)) {
    return [node.name.getText(), node]
  }
  if (ts.isConstructorDeclaration(node)) return ['constructor', node]
  if (
    ts.isVariableDeclaration(node) &&
    ts.isIdentifier(node.name) &&
    node.initializer &&
    (ts.isArrowFunction(node.initializer) || ts.isFunctionExpression(node.initializer))
  ) {
    // The doc comment of the first declarator sits before `const`/`export`, on the VariableStatement.
    const list = node.parent
    const first = ts.isVariableDeclarationList(list) && list.declarations[0] === node
    return [node.name.text, first && ts.isVariableStatement(list.parent) ? list.parent : node]
  }
  return null
}

/**
 * Check the header and every class and named function in one source file.
 *
 * @param text - The file's text.
 * @param file - Path shown in messages; `.tsx` enables JSX parsing.
 * @param known - Every ID in the reference registry.
 * @returns Problems in source order.
 *
 * @references
 *   [TS-COMPILER-API] ts.createSourceFile, ts.forEachChild,
 *     https://github.com/microsoft/TypeScript/wiki/Using-the-Compiler-API
 */
export function lintSource(text: string, file: string, known: ReadonlySet<string>): Problem[] {
  const kind = file.endsWith('.tsx') ? ts.ScriptKind.TSX : ts.ScriptKind.TS
  const source = ts.createSourceFile(file, text, ts.ScriptTarget.Latest, true, kind)
  const problems: Problem[] = []
  /** 1-based line number of a position. @references [TS-COMPILER-API] */
  const lineOf = (pos: number) => source.getLineAndCharacterOfPosition(pos).line + 1

  const first = (ts.getLeadingCommentRanges(text, 0) ?? []).find(
    (r) => r.kind === ts.SyntaxKind.MultiLineCommentTrivia && text.startsWith('/**', r.pos),
  )
  for (const message of checkComment(first ? text.slice(first.pos, first.end) : null, known)) {
    problems.push({ file, line: 1, name: '<file>', message })
  }

  const names: string[] = []
  /** Check `node` if it is a unit, then its children. @references [TS-COMPILER-API] */
  const visit = (node: ts.Node) => {
    const unit = unitOf(node)
    if (unit) {
      const [name, docNode] = unit
      names.push(name)
      for (const message of checkComment(docBefore(text, docNode.getFullStart(), first?.pos ?? null), known)) {
        problems.push({ file, line: lineOf(node.getStart()), name: names.join('.'), message })
      }
    }
    ts.forEachChild(node, visit)
    if (unit) names.pop()
  }
  visit(source)
  return problems
}

/**
 * Every ID in `references/references.yaml`.
 *
 * @returns The registered IDs.
 *
 * @references
 *   [YAML-NPM] yaml parse(), https://eemeli.org/yaml/
 */
async function knownIds(): Promise<Set<string>> {
  const data = parse(await readFile(join(ROOT, 'references', 'references.yaml'), 'utf8')) as {
    references?: { id: string }[]
  }
  return new Set((data.references ?? []).map((ref) => ref.id))
}

/**
 * The project's TypeScript sources, skipping declaration files.
 *
 * @returns Absolute paths, sorted.
 *
 * @references
 *   [NODE-FS] readdir with recursive, https://nodejs.org/api/fs.html
 */
async function sourceFiles(): Promise<string[]> {
  const files = ROOT_FILES.map((f) => join(WEB, f))
  for (const dir of SCAN_DIRS) {
    for (const entry of await readdir(join(WEB, dir), { recursive: true })) {
      if (/\.tsx?$/.test(entry) && !entry.endsWith('.d.ts')) files.push(join(WEB, dir, entry))
    }
  }
  return files.sort()
}

/**
 * Lint the given files (default: the whole web/ project) and set the exit code.
 *
 * @references
 *   [NODE-FS] readFile, https://nodejs.org/api/fs.html
 */
async function main(): Promise<void> {
  const known = await knownIds()
  const args = process.argv.slice(2)
  const files = args.length ? args.map((f) => join(process.cwd(), f)) : await sourceFiles()
  const problems: Problem[] = []
  for (const file of files) {
    problems.push(...lintSource(await readFile(file, 'utf8'), relative(ROOT, file), known))
  }
  for (const p of problems) console.error(`${p.file}:${p.line}: ${p.name}: ${p.message}`)
  console.log(`lint-citations: ${files.length} TypeScript files, ${problems.length} problems`)
  if (problems.length) process.exitCode = 1
}

if (process.argv[1] && fileURLToPath(import.meta.url) === process.argv[1]) {
  await main()
}
