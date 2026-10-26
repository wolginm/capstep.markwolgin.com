# Capitol Steps Preservation Site — Project Plan

**Status:** Phase 3 COMPLETE (2026-10-26). Phase 4 in progress (approved 2026-10-26).
**Author:** Claude (agent), for wolginm
**Date:** 2026-10-25 (revised 2026-10-25)

---

## 1. Goal

Build a user-friendly index of the Capitol Steps audio that the Internet Archive's
Wayback Machine has already archived. **We do not re-host any audio.** Every track
plays from or links to its Wayback Machine capture. Our site adds the parts the
raw archive listing lacks:

- browsing, searching, and filtering by title, year, album, and topic
- per-song detail pages: parody title, the original song it parodies, the original
  songwriters/artist, album, year, a short description, and every archived format
- clear copyright and attribution for each song, plus a site-wide disclaimer and
  takedown contact
- a full bibliography, and per-method source citations in the code (as `CLAUDE.md`
  requires)

## 2. What we already know (probed 2026-10-25)

A probe of the Wayback CDX API [IA-CDX-API] turned up the following
[WAYBACK-CAPSTEPS-SOUNDS]:

- **Audio files are under `/sounds/`, not `/songs/`.** The `/songs/` pages are HTML
  listings that link to `/sounds/<slug>.<ext>`.
- **One song often has several formats and captures.** Example `401k`:
  `401k.mp3`, `401k.ra`, `401k.ram`, `401k-0812.mp3`, `401k-obamamia.mp3`.
  Formats seen: `.mp3`, `.au`, `.ra`, `.ram` (RealAudio, 1997–2024 captures).
- **The same file shows up under URL variants** (`http`/`https`, `www.`, `:80`),
  so we need to normalize and dedupe.
- **The Wayback API is flaky.** One of four queries returned "Temporarily Offline",
  and one returned nothing. The pipeline must retry with backoff, throttle itself,
  and cache raw responses locally so we never re-query unnecessarily.

## 3. Proposed architecture

```
 ┌────────────────────────┐    ┌───────────────────────┐    ┌──────────────────────┐
 │ 1. Ingestion (Python)  │ →  │ 2. Catalog (JSON +    │ →  │ 3. Website           │
 │  - CDX enumeration     │    │    SQLite, versioned  │    │  React + TypeScript  │
 │  - archived /songs/    │    │    in repo)           │    │  (Vite), static build│
 │    page scraping       │    │                       │    │  audio streams from  │
 │  - metadata enrichment │    │                       │    │  web.archive.org     │
 └────────────────────────┘    └───────────────────────┘    └──────────────────────┘
```

**Decided: a static React + TypeScript (Vite) site.** The catalog only changes when
we re-run ingestion, so we don't need a live backend.

**Hosting: GitHub Pages or self-hosted.** The build must work on both:
- The base path is configurable at build time (Vite `base`), e.g. `/capitol_steps/`
  on GitHub Pages and `/` when self-hosted.
- Routing must survive a hard refresh on a static host that has no server rewrites.
  Pre-render one HTML file per song page, or fall back to hash routing.
- The output is a plain `dist/` folder that any web server (nginx, Caddy, Apache)
  can serve unchanged.

### Audio playback
- **Only `.mp3` is in scope.** Play it with an HTML `<audio>` element pointing at the
  Wayback "raw" capture URL: `https://web.archive.org/web/<timestamp>id_/<original-url>`.
  The `id_` flag serves the original bytes without the Wayback toolbar.
- **Legacy formats (`.au`, `.ra`, `.ram`) are skipped.** The site neither shows nor
  links them.
- Any song that exists **only** in a legacy format goes into
  `reports/legacy_only_songs.md` for the developer to review. That report lists the
  slug, the formats found, the capture timestamps, and the Wayback links.
- Always show a "View on the Wayback Machine" link to the normal capture page.

## 4. Data model (draft)

**Each variant is its own song.** `401k`, `401k-0812`, and `401k-obamamia` are three
separate entries. Album grouping may come later, so the model leaves room for it.

```
Song
  id                 full file slug, e.g. "401k-obamamia"   (unique)
  base_slug          slug before the first "-", e.g. "401k"   (hint for later grouping; not shown)
  title              parody title as shown on capsteps.com
  parody_of          { title, original_artist, songwriters[] }  (v2, nullable)
  albums[]           { title, year }                          (future, nullable)
  year_first_seen    earliest Wayback capture year
  description        short blurb from the archived /songs/ page (quoted, cited)
  topics[]           e.g. "Obama", "Economy"                  (optional, later)
  audio              { original_url, mimetype, best_timestamp, all_timestamps[],
                       wayback_raw_url, wayback_view_url, http_status }   (.mp3 only)
  copyright          { notice, holder, source_ref }
  sources[]          reference IDs from the bibliography
```

## 5. Phases

Every phase ends with a checkpoint where I report back and you approve before I
continue.

### Phase 0 — Scaffolding *(small)*
- Repo layout (below), `git init`, `.gitignore`, README.
- `references/references.yaml`: the single source of truth for citations, keyed by
  ID (e.g. `IA-CDX-API`, `WIKI-CAPSTEPS`).
- `BIBLIOGRAPHY.md`, generated from `references.yaml`.

### Phase 1 — Discovery survey *(read-only, produces a report)*
- Enumerate every capture under `capsteps.com/sounds/*` and `capsteps.com/songs/*`
  through the CDX API, with paging, throttling, retries, and a raw-response cache.
- Report: number of unique songs (one per file slug), formats, captures, year range,
  and broken (non-200) captures. Also: how many `/songs/` listing snapshots exist and
  how their HTML structure changed over the years.
- Produce the first draft of `reports/legacy_only_songs.md`: songs with no `.mp3`
  capture, only `.au`/`.ra`/`.ram`.
- **Checkpoint:** decide scope from these real numbers.

### Phase 2 — Ingestion pipeline (Python)
1. `cdx.py`: fetch, page, cache, and normalize CDX rows.
2. `normalize.py`: canonicalize URLs (scheme/host/port) and group by full file slug
   (one song per slug). Keep `.mp3` only and pick its best capture (status 200,
   preferring the newest). Send legacy-only slugs to the review report.
3. `songs_pages.py`: parse archived `/songs/` listing pages to map audio slugs to
   display titles, descriptions, and album groupings. Separate parsers per page
   era if the HTML changed.
4. *(v2, deferred)* `enrich.py`: look up the original song and songwriters for each
   parody. Candidate sources: MusicBrainz (CC0 data), Wikipedia discography pages,
   the album liner text on capsteps.com. Each value gets a source reference.
   **v1 ships with archive-only data:** titles, descriptions, and audio.
5. `build_catalog.py`: emit `catalog.json` (consumed by the site),
   `catalog.sqlite` (for ad-hoc queries), and `reports/legacy_only_songs.md`.
6. Unit tests with recorded fixtures, so tests never hit the live archive.

#### Phase 2 implementation notes (2026-10-25)
- All five Phase 1 recommendations approved by the developer: full homepage harvest,
  latest capture of other pages, file-name fallback titles (flagged), unarchived-songs
  review report, album text stored as data.
- **The parodied song comes from the archive.** The site itself printed it in brackets
  (`[ Old Man River ]`), so `original_song` is filled in Phase 2. MusicBrainz songwriter
  credits stay in v2.
- New `kind` field (`song`, `lirty-dies`, `radio-show`, `promo`, `interview`), because the
  archive's audio includes radio promos and interviews. The site can filter on it.
- Descriptions are stored only as **excerpts of 300 characters or less** (whole sentences),
  per §6 "quote briefly".
- **Copyright notice:** stored verbatim from the archived footer of the capture where the song
  appeared. Holders were Strauss & Newport, later Strauss, Newport & Eaton, later Newport &
  Eaton. The footer also says *"These audio files are provided for individual listening only.
  Do not redistribute."* The site must show this verbatim and keep the link-only model
  (never copy files).
- `data/catalog.sqlite` is gitignored (regenerable binary); `data/catalog.json` is tracked.
- **Result:** 1,381 archived pages harvested (0 missing), 1,499 captures analysed. The catalog has
  686 playable songs: 95% with archive titles (35 file-name titles, flagged), 77% with the parodied
  song, 50% with an album (45 albums, one archive-wide spelling and year each), 87% with a featured
  week, 94% with a description, and 100% with a copyright notice. 72 legacy-only and 94 unarchived
  songs are listed in `reports/`. Details: `reports/phase2_extraction.md`.
- Album names and years are normalized archive-wide; obvious variants (case, "&"/"and", leading
  "The") are merged, but differently worded names are kept as printed.
- Phase 3 note: `[IA-WAYBACK-URL]` recommends the `if_` flag (not `id_`) for toolbar-free links to
  archived *pages*; audio keeps using `id_` (raw bytes).

### Phase 3 — Website (React + TypeScript, Vite)
- **Home / browse:** searchable, sortable table or grid. Filters: year
  (album filter added once albums exist).
- **Song detail page:** metadata, embedded `.mp3` player, list of capture dates,
  copyright block, sources, and a per-song "Report a copyright issue" mailto link.
- **About:** who the Capitol Steps were (cited), what this site is and isn't.
- **Copyright & takedown page:** see §6.
- **Bibliography page:** rendered from `references.yaml`.
- **Site footer (every page):** must state that the site was developed primarily
  with an LLM, with a human making the decisions. Draft wording: *"Built primarily
  with an AI model (LLM); a human developer drove every decision."* It links to the
  AI Disclosure page. *(Developer requirement, 2026-10-25.)*
- **AI Disclosure page:** documents which LLM was used and how:
  - model and tool: Claude Opus 5.5 (`claude-opus-5-5`), by Anthropic, run through
    the Claude Code CLI
  - the workflow: the human approves a written plan and each phase, the agent writes
    code, docs, and data, and the human reviews and commits
  - what the LLM did (code, pipeline, docs, metadata extraction) and what the human
    decided (stack, scope, copyright policy, formats, variants)
  - per-phase log, sourced from `docs/AI_USAGE.md`. That file is updated at the end
    of every phase from now on.
  - limitations: LLM output can be wrong; every metadata field carries a source
    citation so readers can verify it.
- Accessibility basics: keyboard navigation, labelled audio controls, contrast.
- Tests: Vitest for components and utilities, plus a small Playwright smoke test.

#### Phase 3 implementation notes (2026-10-26)
- Stack as installed: Vite 8, React 19, TypeScript 6, **React Router 8** (declarative mode;
  v8 had replaced v7 by the time of install), Vitest 5, Playwright, oxlint (template default).
- **HashRouter** and `base: './'`: one build works at a domain root or any sub-path
  (GitHub Pages) with no server rewrites. Verified by serving `dist/` under a sub-path.
- Data is fetched at runtime from `web/public/data/` (gitignored copies made by
  `scripts/sync-data.ts`), so `data/`, `references/` and `docs/` stay the single sources.
- The player uses `preload="none"`: nothing is requested from the Internet Archive until
  the listener presses play. The smoke test blocks all archive requests.
- Only archived copyright notices are shown; there is no invented fallback text.
- `web/src/config.ts` holds the takedown address; a test checks it matches `catalog.json`.

### Phase 4 — Citation enforcement and QA
- A lint script that fails if any function/method lacks a `References:` docstring
  section, or cites an ID missing from `references.yaml` (Python: AST walk;
  TypeScript: TSDoc `@see` / custom tag check).
- Link checker: sample Wayback URLs in the catalog and confirm they still resolve.

### Phase 5 — Deployment
- **GitHub Pages:** GitHub Actions workflow (lint, test, build, deploy to Pages).
- **Self-hosted:** document copying `dist/` to any static web server, with a sample
  nginx/Caddy config.

## 6. Copyright and attribution approach

- **No audio, lyrics, or artwork is copied into this repo or served from our host.**
  Users stream directly from the Internet Archive.
- Each song page shows: "© Capitol Steps" (the notice exactly as it appeared in the
  archived capture, with a citation), plus credits for the original composition
  where known (e.g. "Parody of *Mamma Mia*, written by B. Andersson, B. Ulvaeus,
  S. Anderson").
- We quote descriptions only briefly, always cited with the capture URL and timestamp.
- Site-wide disclaimer: unofficial fan/preservation index, not affiliated with the
  Capitol Steps; all rights belong to their holders.
- **Takedown contact:** `wolginmark@gmail.com`. Every takedown link is a `mailto:` with
  a pre-filled subject of `COPYRIGHT TAKEDOWN NOTICE -- <song title>`. On the general
  Copyright page, the suffix is left for the sender to complete:
  `COPYRIGHT TAKEDOWN NOTICE -- `.
  The address lives in a single config value (`web/src/config.ts`) so it can be
  changed in one place.

## 7. Citation convention

**Python docstring (Google style):**
```python
def fetch_cdx(prefix: str) -> list[CdxRow]:
    """Fetch all Wayback CDX rows under a URL prefix.

    Args:
        prefix: URL prefix, e.g. "capsteps.com/sounds/".

    Returns:
        Parsed CDX rows.

    References:
        [IA-CDX-API] Internet Archive, "Wayback CDX Server API",
            https://github.com/internetarchive/wayback/tree/master/wayback-cdx-server
    """
```

**TypeScript (TSDoc):**
```ts
/**
 * Build the raw-bytes Wayback URL for a capture.
 *
 * @references
 *   [IA-WAYBACK-URL] Internet Archive, Wayback Machine URL flags (`id_`), <url>
 */
```

`BIBLIOGRAPHY.md` collects every reference ID in one place, with its full citation
and where it's used.

## 8. Proposed repo layout

```
capitol_steps/
  CLAUDE.md
  plan/PLAN.md
  docs/AI_USAGE.md        # running log of LLM use; feeds the AI Disclosure page
  BIBLIOGRAPHY.md
  references/references.yaml
  ingest/                 # Python 3.12, uv or venv
    capsteps_ingest/ {cdx,normalize,songs_pages,enrich,build_catalog}.py
    tests/ (fixtures/)
    cache/                # raw CDX/HTML responses (gitignored)
  data/catalog.json
  reports/legacy_only_songs.md   # songs with no .mp3, for developer review
  web/                    # React + TS (Vite)
    src/ {pages,components,lib}/
  tools/check_citations.py
```

## 9. Decisions (resolved by developer, 2026-10-25)

1. **Frontend stack:** React + TypeScript (Vite) static site. ✅
2. **Hosting target:** GitHub Pages or self-hosted. The build supports both (§3). ✅
3. **Metadata enrichment:** v1 uses archive-only data; parody-of and songwriter
   credits come in v2. ✅
4. **Legacy formats:** skipped. No `.au` (and, by the same reasoning, no `.ra`/`.ram`)
   on the site. Songs that exist only in legacy formats are written to
   `reports/legacy_only_songs.md` for review. ✅
   *Agent's interpretation: "skip .au" was taken to cover every non-playable legacy
   format. Revisit if `.ra`/`.ram` should be treated differently.*
5. **Takedown contact:** `wolginmark@gmail.com`, subject
   `COPYRIGHT TAKEDOWN NOTICE -- <song title>`. ✅
6. **Variants:** each variant (e.g. `401k-obamamia`) is its own song. Album grouping
   may come later; `base_slug` is kept as a hint for it. ✅
7. **Node.js (2026-10-25):** Node 24 LTS, installed by the developer. The machine had Ubuntu's
   Node 18 (end-of-life), which current Vite 8, Vitest 5 and React Router 7 do not support.
   Pinning older tools for Node 18 was rejected. ✅

## 10. Risks

| Risk | Mitigation |
|---|---|
| Wayback API outages / rate limits | Throttle (~1 req/s), exponential backoff, local cache, resumable runs |
| Wayback captures disappear later | Link checker in CI; store the timestamp of every capture we know of, not just one |
| `/songs/` HTML structure changed between eras | Per-era parsers, chosen using the Phase 1 survey |
| Songwriter attribution errors | Every enriched field carries a source ID; mark unverified values |
| Copyright complaints | Link-only model, clear disclaimer, takedown process |
| Citation requirement drift | Automated citation lint in Phase 4, enforced in CI |

---

**Next step on approval:** Phase 0 (scaffolding), then Phase 1 (read-only survey).
