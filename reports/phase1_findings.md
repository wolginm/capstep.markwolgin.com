# Phase 1 Findings and Recommendations

_Written 2026-10-25 by Claude (LLM agent) from the generated Phase 1 reports. Sources:
Wayback CDX index [WAYBACK-CAPSTEPS-SOUNDS] via [IA-CDX-API]; archived pages fetched with
the Wayback `id_` form [IA-WAYBACK-URL]._

Detailed, regenerable reports:

| Report | Contents |
|---|---|
| `phase1_survey.md` | Headline numbers, formats, statuses, years, site inventory |
| `phase1_audio_inventory.csv` | One row per song (852), with best `.mp3` capture |
| `phase1_listing_pages.md` | Candidate listing pages, one capture per year, link counts and structure |
| `phase1_link_titles.csv` | Every song link's text, flagged generic or candidate title |
| `phase1_candidate_pages.csv` | HTML URLs whose path suggests song listings |
| `legacy_only_songs.md` | **For developer review:** 72 songs with no playable `.mp3` |

Regenerate with `uv run python -m capsteps_ingest.survey` and
`uv run python -m capsteps_ingest.pages` from `ingest/`. Raw responses are cached in
`ingest/cache/`, so re-runs make no network requests.

## 1. What the archive holds

| | |
|---|---|
| Songs (unique audio file slugs; each variant is its own song) | **852** |
| Songs with a playable `.mp3` capture (**in scope for the site**) | **686** |
| Songs with only legacy formats (`.au`/`.ra`/`.ram`/`.rm`), listed for review | 72 |
| Songs with no usable capture at all (every capture is a 404 or redirect) | 94 |
| Audio capture years | 1997 – 2026 |

- **All audio lives under `/sounds/`.** No other directory serves audio.
- **There is no `/songs/` page.** `capsteps.com/songs/` has zero captures in the CDX index
  under every URL spelling. The Wayback link in `CLAUDE.md` resolves to nothing. The audio
  was linked from the **homepage** and a few other pages instead (§2).
- **The 94 "no usable capture" songs** are mostly `.mp3` links the crawler found in 2011
  (46 songs) or 2026 (8 songs) that returned 404. The links existed, but the files were
  never archived.
- **Duplicate URL spellings are common.** 359 songs appear under more than one spelling
  (`http`/`https`, `www.`, `:80`). The pipeline already merges them.

## 2. Where the song titles and details are

| Page | Years with audio links | What it holds |
|---|---|---|
| `capsteps.com/` (homepage) | 1996 – 2021 | The **main source**: 4–16 featured songs at a time, each with a title, a topical description, and often the album |
| `capsteps.com/index.html` | 1998 – 2008 | Same as the homepage in that era |
| `capsteps.com/radio/` | 1997 – 2023 | Radio show listings (large pages, few audio links) |
| `capsteps.com/albums/` | 1997 – 2026 | Album list, 1–3 audio links |
| `capsteps.com/albums/songs.html` | 1997 – 2024 | "Songs of The Capitol Steps": **no audio links**. It is an **album → track-title list** (e.g. *"First Lady and the Tramp" (Songs of 1999): On The Dole Again!, …*), but it lists titles only, not file links, and stops at the 2000 album |
| `capsteps.com/sounds/` | — | Directory index, empty or near-empty (0–515 bytes) |

**Page structure changed over three eras**, so Phase 2 needs one parser per era:

1. **1996 – 2010: table layout.** In 2005 and later, each song sits between
   `<!--song-begin -->` / `<!--song-end -->` comments, with a "Week of …" date, a description
   paragraph, and "From the album *X*". The link text is a format label ("MP3 format",
   "[Download", "Streaming]"), so **the title must be taken from nearby markup, not the link**.
2. **2011 – 2021: CSS layout.** Song sections have an `<h3>` heading and a description; the
   title is the link text (e.g. *"Night-Mayor on M Street"*), followed by an album line
   ("From …").
3. **2022 – 2026: post-shutdown.** The homepage carries no audio links.

**Coverage so far:** sampling only **one capture per page per year** (156 snapshots), 251 of
the 852 songs are linked from a sampled page, and 119 have a usable title in the link text.
The homepage changed often: it has **1,209 distinct versions** (plus 46 of
`/index.html`), per CDX `collapse=digest`. Most songs were featured for only a few weeks,
which yearly sampling misses.

## 3. Recommendations for Phase 2 (need your decision)

1. **Fetch every distinct homepage version** (~1,255 captures). This is the only way to
   reach most of the 686 playable songs. At the polite rate (one request per 5 s) it is a
   **one-time ~1h45m run**, cached and resumable. *Recommended.*
2. **Also fetch the latest good capture of every other archived HTML page** (~550 URLs,
   about 45 min): `/radio/`, `/special/*` (Christmas pages, etc.), `/news/`, `/live/`. This
   picks up songs that were never on the homepage. *Recommended.*
3. **Songs whose title is never found:** show a title derived from the file name (e.g.
   `campaign2012-hello` → "Campaign2012 Hello") with a visible "title not found in archive"
   note, rather than hiding the song. *Recommended.*
4. **The 94 songs with no usable audio:** leave them off the site, and list them in a second
   review document (`reports/unarchived_songs.md`) alongside the legacy-only list.
   *Recommended.*
5. **Albums come almost free.** "From the album *X*" appears inside the song blocks in both
   major eras, and `/albums/songs.html` lists track titles per album up to 2000 (matching
   titles to files would be fuzzy). Phase 2 can capture
   the album text *as data* now (not yet used for grouping on the site), so the grouping you
   mentioned for later costs nothing extra. *Recommended.*

## 4. Problems found and fixed during Phase 1

- The archive returned "Temporarily Offline", 503 and 504 errors during the run. The client's
  retry-with-backoff handled them, and nothing was lost.
- Some captures (e.g. `/sounds/` in 2003) are real **zero-byte** responses. My first page
  validator mistook them for outages and retried them for up to 16 minutes each. Fixed:
  only the explicit outage page is retried. A test now covers this.
- About 20 junk URLs (`...mp3&gt`, `...rae`, `...mp3&lm=16777216`) are crawler artifacts
  of malformed links. They are excluded from the song count.
