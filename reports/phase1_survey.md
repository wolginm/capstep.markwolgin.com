# Phase 1 Survey: capsteps.com in the Wayback Machine

_Generated 2026-10-25 by `ingest/capsteps_ingest/survey.py` (0 live CDX requests this run; other responses came from cache)._
_Sources: [IA-CDX-API], [WAYBACK-CAPSTEPS-SOUNDS], [WAYBACK-CAPSTEPS-SONGS]._

## Headline numbers

| Measure | Count |
|---|---|
| Unique archived URLs on the domain | 2271 |
| Audio captures (all formats, all statuses) | 5063 |
| Songs (unique audio file slugs; each variant is its own song) | 852 |
| Songs with a playable `.mp3` capture (in scope for the site) | 686 |
| Songs with **only** legacy-format captures (see `legacy_only_songs.md`) | 72 |
| Songs whose every capture is an error/redirect (no usable audio) | 94 |
| Songs captured under more than one URL spelling | 359 |
| Audio-MIME captures without an audio extension (not grouped) | 20 |
| Audio capture years | 1997 – 2026 |
| Candidate song-listing HTML pages (see `phase1_candidate_pages.csv`) | 52 |

## Audio captures by format

| Extension | Captures |
|---|---|
| `mp3` | 3449 |
| `ram` | 950 |
| `au` | 297 |
| `ra` | 273 |
| `rm` | 74 |

## Audio captures by HTTP status

`-` is a `warc/revisit` record (byte-identical to an earlier capture).

| Status | Captures |
|---|---|
| `200` | 4120 |
| `301` | 370 |
| `404` | 294 |
| `-` | 259 |

## Songs by directory

| Directory | Songs |
|---|---|
| `/sounds/` | 852 |
| `//sounds/` | 1 |

## Songs by year first archived

| Year | New songs |
|---|---|
| `1997` | 15 |
| `1998` | 30 |
| `1999` | 26 |
| `2000` | 46 |
| `2001` | 19 |
| `2002` | 1 |
| `2003` | 2 |
| `2004` | 43 |
| `2005` | 45 |
| `2006` | 54 |
| `2007` | 50 |
| `2009` | 1 |
| `2010` | 2 |
| `2011` | 113 |
| `2012` | 28 |
| `2013` | 133 |
| `2014` | 60 |
| `2015` | 43 |
| `2016` | 30 |
| `2017` | 21 |
| `2018` | 15 |
| `2019` | 17 |
| `2020` | 25 |
| `2021` | 16 |
| `2022` | 1 |
| `2023` | 1 |
| `2024` | 4 |
| `2025` | 2 |
| `2026` | 9 |

## Audio captures by year

| Year | Captures |
|---|---|
| `1997` | 29 |
| `1998` | 122 |
| `1999` | 134 |
| `2000` | 311 |
| `2001` | 62 |
| `2002` | 2 |
| `2003` | 3 |
| `2004` | 190 |
| `2005` | 561 |
| `2006` | 815 |
| `2007` | 808 |
| `2008` | 1 |
| `2009` | 84 |
| `2010` | 4 |
| `2011` | 166 |
| `2012` | 71 |
| `2013` | 239 |
| `2014` | 166 |
| `2015` | 137 |
| `2016` | 168 |
| `2017` | 32 |
| `2018` | 36 |
| `2019` | 38 |
| `2020` | 101 |
| `2021` | 560 |
| `2022` | 34 |
| `2023` | 61 |
| `2024` | 27 |
| `2025` | 59 |
| `2026` | 42 |

## Site inventory: top-level paths (top 30)

| Path | Unique URLs |
|---|---|
| `/sounds/` | 1333 |
| `/images/` | 538 |
| `/live/` | 124 |
| `/` | 75 |
| `/news/` | 52 |
| `/lirty/` | 37 |
| `/img-sys/` | 24 |
| `/special/` | 19 |
| `/css/` | 12 |
| `/about/` | 9 |
| `/.well-known/` | 8 |
| `/albums/` | 7 |
| `/starr/` | 6 |
| `/cgi-sys/` | 6 |
| `/video/` | 4 |
| `/radio/` | 3 |
| `/%3EThe%20Capital%20Steps%3C/` | 2 |
| `/cgi-bin/` | 2 |
| `/2006/` | 1 |
| `/%3eThe+Capital+Steps%3c/` | 1 |
| `/adx/` | 1 |
| `/comlist_files/` | 1 |
| `/ezine/` | 1 |
| `/feed/` | 1 |
| `/feeds/` | 1 |
| `/js/` | 1 |
| `/rss/` | 1 |
| `/static/` | 1 |

## Site inventory: MIME types (top 15)

| MIME type | Unique URLs |
|---|---|
| `text/html` | 551 |
| `audio/mpeg` | 540 |
| `image/jpeg` | 379 |
| `audio/x-pn-realaudio` | 207 |
| `audio/x-mpeg` | 135 |
| `audio/basic` | 121 |
| `image/gif` | 91 |
| `unk` | 67 |
| `image/png` | 44 |
| `application/pdf` | 42 |
| `audio/x-realaudio` | 32 |
| `application/vnd.rn-realmedia` | 21 |
| `text/css` | 11 |
| `application/postscript` | 7 |
| `image/svg+xml` | 4 |

## Caveats

- **`.ram` files are pointers, not audio.** A RealAudio `.ram` metafile holds the address of a separate `.ra`/`.rm` stream, so a status-200 `.ram` capture does not mean the audio itself was archived. This affects only the legacy-only list, since legacy formats are out of scope for the site.
- **The inventory shows only each URL's first capture.** `collapse=urlkey` returns one row per URL, so a page that first returned 404 may have been archived successfully later.
- **`/songs/` is absent.** No `capsteps.com/songs/` URL appears in the CDX index under any spelling; see `phase1_listing_pages.md` for the pages that actually linked to the audio.
- **Junk URLs are excluded.** Audio-MIME rows without an audio extension (e.g. `...mp3&gt`, `...rae`) are crawler artifacts of malformed links, not separate songs.

## Audio-MIME captures without an audio extension (first 25)

| Original URL | Timestamp | MIME |
|---|---|---|
| `http://www.capsteps.com:80/sounds/aljazeera.mp3&lm=16777216` | 20041022014617 | text/html |
| `http://www.capsteps.com:80/sounds/aolguy.rae` | 20000301184424 | text/html |
| `http://www.capsteps.com:80/sounds/bossatnasa.rae` | 20000302005403 | text/html |
| `http://www.capsteps.com:80/sounds/bush-dubyadoodle.mp3&lm=16777216` | 20041026091006 | text/html |
| `http://www.capsteps.com:80/sounds/chelseagirl.rae` | 20000511105953 | text/html |
| `http://www.capsteps.com:80/sounds/cheney-edwards.mp3&gt` | 20041223214240 | text/html |
| `http://www.capsteps.com:80/sounds/flowers-arafat.mp3&gt` | 20041214231859 | text/html |
| `http://www.capsteps.com:80/sounds/forbes.rae` | 20000303200557 | text/html |
| `http://www.capsteps.com:80/sounds/fuel.mp3&lm=16777216` | 20041022020457 | text/html |
| `http://www.capsteps.com/sounds/gibson-mensch.mp3_` | 20210506141738 | text/html |
| `https://www.capsteps.com/sounds/gibson-mensch.mp3_` | 20210506141738 | text/html |
| `http://www.capsteps.com:80/sounds/gore-puttengrand.rae` | 20001017135648 | text/html |
| `http://www.capsteps.com:80/sounds/hillary-evita.rae` | 20001017162258 | text/html |
| `http://www.capsteps.com:80/sounds/hillary2004.mp3&gt` | 20041213201848 | text/html |
| `http://www.capsteps.com:80/sounds/india.rae` | 20000511143506 | text/html |
| `http://www.capsteps.com:80/sounds/kerrybush-swingstates.mp3&gt` | 20041223214306 | text/html |
| `http://www.capsteps.com:80/sounds/kids-pc.rae` | 20000511153849 | text/html |
| `http://www.capsteps.com:80/sounds/mccain-campaign.rae` | 20000407115401 | text/html |
| `http://www.capsteps.com:80/sounds/monica-whosonfirst.mp3,7a0fe0` | 20140416094455 | text/html |
| `http://www.capsteps.com:80/sounds/paranoia-tomridge.mp3&gt` | 20050301050655 | text/html |

