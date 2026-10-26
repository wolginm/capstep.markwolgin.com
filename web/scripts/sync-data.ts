/**
 * Copy the site's data into `web/public/data/` before `dev`, `build` and `test`.
 *
 * - `data/catalog.json` -> `catalog.json` (written by the Python pipeline)
 * - `references/references.yaml` -> `references.json` (for the Bibliography page)
 * - `docs/AI_USAGE.md` -> `AI_USAGE.md` (for the AI Disclosure page)
 *
 * The repository files stay the single source of truth; the copies are gitignored.
 * Runs directly on Node 24 (TypeScript type stripping): `node scripts/sync-data.ts`.
 *
 * @references
 *   [NODE-TYPESCRIPT] Node.js type stripping, https://nodejs.org/api/typescript.html
 *   [NODE-FS] fs/promises, https://nodejs.org/api/fs.html
 *   [YAML-NPM] yaml parse(), https://eemeli.org/yaml/
 *   [VITE-ASSETS] Vite public directory, https://vite.dev/guide/assets.html
 */

import { copyFile, mkdir, readFile, writeFile } from 'node:fs/promises'
import { dirname, join } from 'node:path'
import { fileURLToPath } from 'node:url'
import { parse } from 'yaml'

const WEB = join(dirname(fileURLToPath(import.meta.url)), '..')
const ROOT = join(WEB, '..')
const OUT = join(WEB, 'public', 'data')

/**
 * Convert the reference registry to JSON, keeping only the fields the site shows.
 *
 * @param yamlText - Contents of `references/references.yaml`.
 * @returns Pretty-printed JSON array of references.
 *
 * @references
 *   [YAML-NPM] yaml parse(), https://eemeli.org/yaml/
 */
export function referencesToJson(yamlText: string): string {
  const data = parse(yamlText) as { references?: Record<string, unknown>[] }
  const fields = ['id', 'title', 'url', 'accessed', 'author', 'publisher', 'note']
  const refs = (data.references ?? []).map((ref) =>
    Object.fromEntries(fields.filter((f) => ref[f] !== undefined).map((f) => [f, String(ref[f])])),
  )
  return JSON.stringify(refs, null, 2) + '\n'
}

/**
 * Write all three data files into `web/public/data/`.
 *
 * @references
 *   [NODE-FS] mkdir, copyFile, readFile, writeFile, https://nodejs.org/api/fs.html
 */
async function main(): Promise<void> {
  await mkdir(OUT, { recursive: true })
  await copyFile(join(ROOT, 'data', 'catalog.json'), join(OUT, 'catalog.json'))
  await copyFile(join(ROOT, 'docs', 'AI_USAGE.md'), join(OUT, 'AI_USAGE.md'))
  const yamlText = await readFile(join(ROOT, 'references', 'references.yaml'), 'utf8')
  await writeFile(join(OUT, 'references.json'), referencesToJson(yamlText))
  console.log(`sync-data: wrote catalog.json, references.json, AI_USAGE.md to ${OUT}`)
}

if (process.argv[1] && fileURLToPath(import.meta.url) === process.argv[1]) {
  await main()
}
