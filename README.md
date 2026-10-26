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

Phases 0–3 are complete: discovery, the ingestion pipeline (686 playable recordings), and
the website. See [`plan/PLAN.md`](plan/PLAN.md) for the plan and the current phase.

The site was built primarily with an AI model (LLM), with a human developer driving every
decision; see [`docs/AI_USAGE.md`](docs/AI_USAGE.md).

## Running the website

Requires Node.js 24 (`nvm use` reads `.nvmrc`) [NVM-SH].

```bash
cd web
npm install
npm run dev        # http://localhost:5173/
npm test           # unit and component tests (Vitest)
npx playwright install chromium && npm run test:e2e   # browser smoke test
npm run build      # static site in web/dist/
```

`npm run dev`, `build` and `test` first copy `data/catalog.json`, the reference
registry and `docs/AI_USAGE.md` into `web/public/data/` (`scripts/sync-data.ts`).
The build uses relative paths and hash-based routes, so `web/dist/` can be served
from any static host or sub-path, including GitHub Pages [VITE-STATIC-DEPLOY]
[REACT-ROUTER-HASHROUTER].

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
| `tools/` | Repo tooling (bibliography generator; later the citation lint) |
| `ingest/` | Python pipeline: Wayback CDX → catalog (Phase 1–2) |
| `data/` | Generated `catalog.json` consumed by the site |
| `reports/` | Review documents, e.g. `legacy_only_songs.md` |
| `web/` | React + TypeScript (Vite) static site |
| `docs/AI_USAGE.md` | Log of how the LLM was used; shown on the site's AI Disclosure page |

## Citations

Every source consulted or borrowed from is registered in
`references/references.yaml` and cited by ID in square brackets, e.g.
`[IA-CDX-API]`. Python functions carry a `References:` section in their Google-style
docstrings [GOOGLE-PYGUIDE]; TypeScript uses TSDoc comments with a `@references`
block tag declared in `web/tsdoc.json` [MS-TSDOC] [TSDOC-CONFIG].

Regenerate the bibliography after adding or citing a reference:

```bash
python3 tools/build_bibliography.py          # write BIBLIOGRAPHY.md
python3 tools/build_bibliography.py --check  # CI: fail if stale
```

Requires Python 3.12+ and PyYAML.
