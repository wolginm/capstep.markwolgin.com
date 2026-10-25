# AI Usage Log

This site was developed **primarily with a large language model (LLM)**, with a
**human developer driving every decision**. This log records which model was used
and how. It is the source for the site's AI Disclosure page (plan §5, Phase 3) and
is updated at the end of every phase.

## Model and tooling

| | |
|---|---|
| Model | Claude Opus 5.5 (`claude-opus-5-5`) |
| Vendor | Anthropic |
| Interface | Claude Code (Anthropic's command-line coding agent), run in the developer's local terminal |
| Agent permissions | Read/write within the project directory and shell commands. Every phase starts only with the developer's explicit approval (see `CLAUDE.md`) |

## How the work is divided

**The human developer decides:**
- project goals and scope (`CLAUDE.md`)
- technology stack and hosting (React + TypeScript static site; GitHub Pages or self-hosted)
- content policy: link-only (no re-hosting of audio), `.mp3` only, legacy formats
  (`.au`/`.ra`/`.ram`) skipped and listed for review, each variant is its own song
- the copyright/takedown contact and wording
- the requirement to disclose LLM use (this log, the site footer, and the disclosure page)
- approval of every phase and of every commit

**The LLM (Claude) does:**
- drafts and revises the plan (`plan/PLAN.md`) for the human to review
- writes the code (Python ingestion pipeline, tooling, and later the website), tests, and docs
- queries the Internet Archive and summarizes the findings in reports
- keeps the citation registry (`references/references.yaml`) and bibliography up to date
- reports results, including failures and open questions, back to the human

**Verification:** LLM output can be wrong. Every source is cited by ID and listed in
`BIBLIOGRAPHY.md`, and data fields will carry source citations so readers can check them.
Automated tests cover the pipeline logic.

## Phase log

### Phase 0 — Scaffolding (2026-10-25)
- **Human:** wrote `CLAUDE.md`; reviewed the draft plan; resolved six open decisions
  (stack, hosting, enrichment timing, legacy formats, takedown contact, variants);
  approved Phase 0 and the commit.
- **LLM:** probed the Wayback CDX API to ground the plan, drafted `plan/PLAN.md`, and
  created the repo layout, `.gitignore`, `README.md`, the citation registry, and
  `tools/build_bibliography.py`. Found and fixed a false-positive bug in its own
  citation scanner during testing.

### Phase 1 — Discovery survey (2026-10-25)
- **Human:** approved Phase 1; added the requirement for the LLM-disclosure footer
  and this AI Disclosure page.
- **LLM:** wrote the CDX client (`ingest/capsteps_ingest/cdx.py`: throttling, retries,
  resume-key paging, disk cache), URL normalization (`urls.py`), the survey
  (`survey.py`), and unit tests. Ran the survey and produced the reports in `reports/`.
  Found that `capsteps.com/songs/` has **no** captures in the CDX index; the audio
  lives under `/sounds/` and was linked from the homepage. Added a listing-page sampler
  (`pages.py`), and wrote `reports/phase1_findings.md` with recommendations for Phase 2.
  Found and fixed its own bug (zero-byte captures mistaken for outages) mid-run; 32 tests pass.

### Phase 2 — Ingestion pipeline (2026-10-25)
- **Human:** approved all five Phase 1 recommendations (full homepage harvest, other
  pages, file-name fallback titles, unarchived-songs report, album text as data) and
  the Phase 1 commit.
- **LLM:** wrote the harvester (`harvest.py`, ~1,400 archived pages fetched politely and
  cached), the era-aware extractor (`extract.py`: titles, parodied song, album, week,
  description, copyright notice), and the offline catalog builder (`build_catalog.py`:
  `data/catalog.json`, SQLite, review reports). While checking output against real
  pages it found and fixed several of its own extraction errors: real titles containing
  "Here" rejected as format labels, an over-long copyright match, drop-cap repair joining
  "A town", and prose links taken as titles. Each fix has a regression test.
- **Human:** paused the work overnight (the LLM left a resume bookmark) and approved resuming.
- **LLM:** finished the harvest (1,381 pages, 0 missing; one run was stopped by the tool when the
  machine ran low on memory and resumed from cache). Reviewed the full catalog and spot-checked
  random entries against their archived pages, then fixed further errors of its own: format
  labels ("RA Streaming", "(MP3)") and prose links ("the Bush tax cut rates") taken as titles,
  site navigation leaking into descriptions, blurbs starting mid-sentence, untidy and
  inconsistent album names, and site prompts ("Read more Lirty Dies") taken as parodied songs.
  Found a citable description of the Wayback `id_` URL flag. 65 tests pass. Result: 686
  playable songs, 95% with titles from the archive.
