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
- writes the code (Python ingestion pipeline, tooling, and the website), tests, and docs
- queries the Internet Archive and summarizes the findings in reports
- keeps the citation registry (`references/references.yaml`) and bibliography up to date
- reports results, including failures and open questions, back to the human

## Limitations and verification

- **LLM output can be wrong.** The song details on this site were extracted from archived
  capsteps.com pages by rules the LLM wrote and then checked against samples of those pages;
  some titles, albums, dates or descriptions may still be wrong or missing.
- Titles the archive never printed are made from the file name and are marked
  "file-name title" on the site.
- **Check the source.** Every song page links to the archived pages its details came from,
  and every source the project uses is cited by ID and listed in the Bibliography.
- Automated tests cover the pipeline and the website, but they test the rules, not every
  one of the 686 entries.
- Corrections are welcome through the contact address on the Copyright & takedown page.

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

### Phase 3 — Website (2026-10-26)
- **Human:** approved Phase 3 and the Phase 2 commit; installed Node.js 24 LTS (with nvm)
  after choosing it over pinning older tools for the system's end-of-life Node 18.
- **LLM:** scaffolded the React + TypeScript site with Vite (`web/`): Browse (search, filters
  by kind/album/year, sorting, shareable URLs), song pages (player streaming straight from
  the Wayback Machine, nothing preloaded; archived copyright notice quoted verbatim; capture
  dates; sources; pre-filled takedown link), About, Copyright & takedown, Bibliography, and
  this page, which renders this log. The LLM-disclosure footer is on every page. Checked
  library versions and APIs against current documentation before use (React Router had
  reached v8). Verified colour contrast by calculation and that the build works under a
  sub-path. Caught its own mistakes in testing: a comment closed early by a `*/` inside a
  URL, and an invented fallback copyright line, removed so only archived notices are shown.
  36 unit/component tests and 2 browser smoke tests pass.

### Phase 4 — Citation enforcement and QA (2026-10-26)
- **Human:** reviewed the running site, approved the Phase 3 commit and Phase 4.
- **LLM:** wrote two citation lints, one for Python (`tools/lint_citations.py`) and one for
  TypeScript (`web/scripts/lint-citations.ts`). Each fails if a file, class or named
  function lacks a references section, or cites a source missing from the bibliography.
  They found 11 small nested helpers without one, which were then documented. Also fixed
  the bibliography tool, which only warned about unknown citations although it was meant
  to fail. Wrote a polite link checker. Its first run found all 83 links working (20
  sampled recordings, which must return audio rather than an error page, and every
  reference). Caught its own mistake in testing: the lint at first took the word
  "References:" written in prose for a real section, so one docstring passed by accident.
  24 tool tests and 49 web tests pass.

### Phase 5 — Deployment (2026-11-06)
- **Human:** committed Phase 4 and approved the Phase 5 plan. Decided the link check runs
  monthly rather than on every push, since the archived captures are not expected to
  change. Creates the GitHub repository, pushes, and turns on Pages; the agent does not.
- **LLM:** wrote the GitHub Actions workflows. One runs every lint and test, builds the
  site and deploys `main` to GitHub Pages. The other runs the link checker monthly. Also
  wrote a self-hosting guide with sample nginx and Caddy configs, and added 21 cited
  sources, checking that each URL resolves. Checked the current version of each action
  rather than relying on memory. Caught its own mistake while checking against GitHub's
  documentation: it had claimed that GitHub limits Pages deployments to `main` by
  itself, which GitHub only recommends. The guide now says to add that rule. Could not
  run nginx, Caddy or a workflow linter in its sandbox, so those configs were checked by
  reading and by YAML parsing only. The real test is the first run on GitHub.

### Phase 5 addendum — Custom domain (2026-11-16)
- **Human:** created the GitHub repository `wolginm/capstep.markwolgin.com` and chose the
  domain `capstep.markwolgin.com`. Owns the DNS and the GitHub settings.
- **LLM:** checked GitHub's current custom-domain, domain-verification and HTTPS
  documentation, and wrote the setup steps in the order GitHub recommends: add the domain
  before creating the DNS record. Found that no code change and no `CNAME` file is needed
  for an Actions-deployed site. Removed one claim it could not source, that the old
  `github.io` address redirects to the custom domain. Checked that the site loads nothing
  over plain `http://`, so enforcing HTTPS will not cause mixed-content warnings.
