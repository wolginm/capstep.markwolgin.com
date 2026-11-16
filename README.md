# Capitol Steps Preservation Site

An unofficial, user-friendly index of the Capitol Steps audio archived by the
Internet Archive's Wayback Machine [WAYBACK-CAPSTEPS-SONGS]. The Capitol Steps were
an American political-satire troupe that performed song parodies from 1981 to 2020
and announced their shutdown in January 2021 [WIKI-CAPSTEPS].

**This project hosts no audio.** Every track streams from, or links to, its
Wayback Machine capture. This site adds search, song details, and copyright
attribution on top.

> Not affiliated with the Capitol Steps. All recordings and lyrics belong to their
> respective rights holders. Copyright concerns:
> [wolginmark@gmail.com](mailto:wolginmark@gmail.com?subject=COPYRIGHT%20TAKEDOWN%20NOTICE%20--%20)
> with the subject line `COPYRIGHT TAKEDOWN NOTICE -- <song title>`.

## Status

Phases 0–5 are complete: discovery, the ingestion pipeline (686 playable recordings), the
website, citation and link checks, and deployment. See [`plan/PLAN.md`](plan/PLAN.md) for the plan.

The site was built primarily with an AI model (LLM), with a human developer driving every
decision; see [`docs/AI_USAGE.md`](docs/AI_USAGE.md).

## Running the website

Requires Node.js 24 (`nvm use` reads `.nvmrc`) [NVM-SH].

```bash
cd web
npm install
npm run dev        # http://localhost:5173/
npm run lint       # oxlint, then the TypeScript citation lint
npm test           # unit and component tests (Vitest)
npx playwright install chromium && npm run test:e2e   # browser smoke test
npm run build      # static site in web/dist/
```

`npm run dev`, `build` and `test` first copy `data/catalog.json`, the reference
registry and `docs/AI_USAGE.md` into `web/public/data/` (`scripts/sync-data.ts`).
The build uses relative paths and hash-based routes, so `web/dist/` can be served
from any static host or sub-path, including GitHub Pages [VITE-STATIC-DEPLOY]
[REACT-ROUTER-HASHROUTER].

## Deploying

GitHub Actions runs every check on each push and pull request, deploys `main` to GitHub
Pages, and checks links once a month (`.github/workflows/`). To self-host, copy
`web/dist/` to any static web server; sample nginx and Caddy configs are in `deploy/`.
Setup steps for both are in [`docs/DEPLOY.md`](docs/DEPLOY.md) [GH-PAGES-CUSTOM-WORKFLOW].
The public site is <https://capstep.markwolgin.com/>, a custom domain on GitHub Pages
[GH-PAGES-CUSTOM-DOMAIN].

## Rebuilding the catalog

```bash
cd ingest
uv run python -m capsteps_ingest.harvest        # polite, cached Wayback download (slow)
uv run python -m capsteps_ingest.build_catalog  # offline: data/catalog.json + reports/
uv run pytest -q
```

## Layout

| Path | Purpose |
|---|---|
| `plan/` | Approved project plan |
| `references/references.yaml` | Single source of truth for every citation |
| `BIBLIOGRAPHY.md` | Generated from `references.yaml`. Do not edit by hand |
| `tools/` | Repo tooling: bibliography generator, citation lint, link checker |
| `ingest/` | Python pipeline: Wayback CDX → catalog (Phase 1–2) |
| `data/` | Generated `catalog.json` consumed by the site |
| `reports/` | Review documents, e.g. `legacy_only_songs.md` |
| `web/` | React + TypeScript (Vite) static site |
| `docs/AI_USAGE.md` | Log of how the LLM was used; shown on the site's AI Disclosure page |
| `docs/DEPLOY.md` | GitHub Pages setup and self-hosting guide |
| `deploy/` | Sample nginx and Caddy configs for self-hosting |
| `.github/workflows/` | CI + Pages deployment, and the monthly link check |

## Citations

Every source consulted or borrowed from is registered in
`references/references.yaml` and cited by ID in square brackets, e.g.
`[IA-CDX-API]`. Python functions carry a `References:` section in their Google-style
docstrings [GOOGLE-PYGUIDE]; TypeScript uses TSDoc comments with a `@references`
block tag declared in `web/tsdoc.json` [MS-TSDOC] [TSDOC-CONFIG].

Regenerate the bibliography after adding or citing a reference, and run the checks:

```bash
python3 tools/build_bibliography.py          # write BIBLIOGRAPHY.md
python3 tools/build_bibliography.py --check  # CI: fail if stale or an unknown ID is cited
python3 tools/lint_citations.py              # every Python unit has a References: section
(cd web && npm run lint:citations)           # every TypeScript unit has @references
python3 tools/check_links.py                 # network: 20 random recordings + every reference URL
uv run --no-project --with pytest --with pyyaml pytest tools/tests   # tests for the tools
```

Both lints require each module, class and named function (methods and nested functions
too) to cite at least one registered ID or say `None`, and reject IDs missing from the
registry. The link checker expects each recording's player URL to return audio, so an
archive error page fails; it sends one small request per second.

Requires Python 3.12+ and PyYAML.
