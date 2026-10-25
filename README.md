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

Phase 0 (scaffolding) is complete. See [`plan/PLAN.md`](plan/PLAN.md) for the full
plan and the current phase.

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
| `web/` | React + TypeScript (Vite) static site (Phase 3) |

## Citations

Every source consulted or borrowed from is registered in
`references/references.yaml` and cited by ID in square brackets, e.g.
`[IA-CDX-API]`. Python functions carry a `References:` section in their Google-style
docstrings [GOOGLE-PYGUIDE]; TypeScript uses TSDoc comments [MS-TSDOC].

Regenerate the bibliography after adding or citing a reference:

```bash
python3 tools/build_bibliography.py          # write BIBLIOGRAPHY.md
python3 tools/build_bibliography.py --check  # CI: fail if stale
```

Requires Python 3.12+ and PyYAML.
