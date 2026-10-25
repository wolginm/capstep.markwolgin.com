"""Phase 1 discovery survey of capsteps.com in the Wayback Machine (read-only).

Enumerates every archived audio capture on capsteps.com and a de-duplicated
inventory of every archived URL, then writes review reports:

- ``reports/phase1_survey.md``           headline numbers and findings
- ``reports/phase1_audio_inventory.csv`` one row per song (file slug)
- ``reports/phase1_candidate_pages.csv`` archived HTML pages that may list songs

Usage:
    uv run python -m capsteps_ingest.survey [--repo-root PATH]

References:
    [IA-CDX-API] https://github.com/internetarchive/wayback/tree/master/wayback-cdx-server
    [WAYBACK-CAPSTEPS-SOUNDS] https://web.archive.org/cdx/search/cdx?url=capsteps.com&matchType=domain&filter=mimetype:audio.*
    [WAYBACK-CAPSTEPS-SONGS] https://web.archive.org/web/20260000000000*/https://www.capsteps.com/songs/
"""

from __future__ import annotations

import argparse
import csv
import re
from collections import Counter, defaultdict
from collections.abc import Iterable
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from urllib.parse import urlsplit

from .cdx import CdxClient, CdxRow
from .urls import AUDIO_EXTS, LEGACY_EXTS, PLAYABLE_EXTS, audio_file, canonical_url, wayback_view_url

DOMAIN = "capsteps.com"
AUDIO_EXT_FILTER = "original:.*\\.(?i:" + "|".join(sorted(AUDIO_EXTS)) + ")(\\?.*)?"
CANDIDATE_PAGE_WORDS = re.compile(r"song|sound|album|audio|listen|music|cd|mp3|parod|track", re.I)
GOOD_STATUSES = {"200", "-"}  # "-" = warc/revisit: identical to an earlier 200 capture


@dataclass
class SongSurvey:
    """Survey facts for one song (one audio file slug; variants are separate songs).

    References:
        [PY-DATACLASSES] dataclasses.field(default_factory=...),
            https://docs.python.org/3/library/dataclasses.html
    """

    slug: str
    captures: list[CdxRow] = field(default_factory=list)

    def _by_ext(self, exts: Iterable[str]) -> list[CdxRow]:
        """Captures whose URL extension is in ``exts``.

        References:
            None (internal helper).
        """
        wanted = set(exts)
        return [row for row in self.captures if (af := audio_file(row.original)) and af.ext in wanted]

    @property
    def formats(self) -> list[str]:
        """Sorted audio extensions seen for this slug.

        References:
            [IA-CDX-API] statuscode / warc/revisit semantics,
                https://github.com/internetarchive/wayback/tree/master/wayback-cdx-server
        """
        return sorted({audio_file(row.original).ext for row in self.captures})

    @property
    def directories(self) -> list[str]:
        """Sorted directories the slug was served from.

        References:
            [IA-CDX-API] statuscode / warc/revisit semantics,
                https://github.com/internetarchive/wayback/tree/master/wayback-cdx-server
        """
        return sorted({audio_file(row.original).directory for row in self.captures})

    @property
    def good_mp3(self) -> list[CdxRow]:
        """MP3 captures with a usable status (200 or revisit), oldest first.

        References:
            [IA-CDX-API] statuscode / warc/revisit semantics,
                https://github.com/internetarchive/wayback/tree/master/wayback-cdx-server
        """
        return sorted(
            (r for r in self._by_ext(PLAYABLE_EXTS) if r.statuscode in GOOD_STATUSES),
            key=lambda r: r.timestamp,
        )

    @property
    def best_mp3(self) -> CdxRow | None:
        """Newest status-200 MP3 capture, falling back to the newest revisit.

        References:
            [IA-CDX-API] statuscode / warc/revisit semantics,
                https://github.com/internetarchive/wayback/tree/master/wayback-cdx-server
        """
        good = self.good_mp3
        ok = [r for r in good if r.statuscode == "200"]
        return (ok or good or [None])[-1]

    @property
    def has_any_mp3_url(self) -> bool:
        """True if any .mp3 URL was crawled, whatever its status.

        References:
            [IA-CDX-API] statuscode / warc/revisit semantics,
                https://github.com/internetarchive/wayback/tree/master/wayback-cdx-server
        """
        return bool(self._by_ext(PLAYABLE_EXTS))

    @property
    def legacy_captures(self) -> list[CdxRow]:
        """Legacy-format captures with a usable status, oldest first.

        References:
            [IA-CDX-API] statuscode / warc/revisit semantics,
                https://github.com/internetarchive/wayback/tree/master/wayback-cdx-server
        """
        return sorted(
            (r for r in self._by_ext(LEGACY_EXTS) if r.statuscode in GOOD_STATUSES),
            key=lambda r: r.timestamp,
        )

    @property
    def first_seen(self) -> str:
        """Earliest capture timestamp.

        References:
            None (internal helper).
        """
        return min(r.timestamp for r in self.captures)

    @property
    def last_seen(self) -> str:
        """Latest capture timestamp.

        References:
            None (internal helper).
        """
        return max(r.timestamp for r in self.captures)


def collect_audio_rows(client: CdxClient) -> list[CdxRow]:
    """Fetch every audio capture on the domain, by extension and by MIME type.

    Two queries are unioned because some audio is served with a generic MIME
    type, and some audio-typed responses lack an audio extension.

    Args:
        client: CDX client.

    Returns:
        Unique capture rows (by timestamp + original URL).

    References:
        [IA-CDX-API] matchType=domain, filter=<field>:<regex>,
            https://github.com/internetarchive/wayback/tree/master/wayback-cdx-server
    """
    seen: dict[tuple[str, str], CdxRow] = {}
    for label, flt in (("by extension", AUDIO_EXT_FILTER), ("by MIME type", "mimetype:audio/.*")):
        client.log(f"Audio captures {label}:")
        for row in client.query(url=DOMAIN, matchType="domain", filter=flt):
            seen.setdefault((row.timestamp, row.original), row)
    return list(seen.values())


def collect_inventory(client: CdxClient) -> list[CdxRow]:
    """Fetch one row per unique archived URL on the domain.

    Args:
        client: CDX client.

    Returns:
        One row per urlkey (the first capture of each URL).

    References:
        [IA-CDX-API] collapse=urlkey,
            https://github.com/internetarchive/wayback/tree/master/wayback-cdx-server
    """
    client.log("Unique URL inventory:")
    return list(client.query(url=DOMAIN, matchType="domain", collapse="urlkey"))


def group_songs(audio_rows: Iterable[CdxRow]) -> dict[str, SongSurvey]:
    """Group audio captures into songs keyed by lower-cased file slug.

    Args:
        audio_rows: Capture rows from :func:`collect_audio_rows`.

    Returns:
        Mapping of slug to :class:`SongSurvey`. Rows whose URL has no audio
        extension (MIME-only matches) are skipped here and counted separately.

    References:
        [PY-COLLECTIONS] defaultdict-style grouping,
            https://docs.python.org/3/library/collections.html
    """
    songs: dict[str, SongSurvey] = {}
    for row in audio_rows:
        af = audio_file(row.original)
        if af is None:
            continue
        songs.setdefault(af.slug, SongSurvey(af.slug)).captures.append(row)
    return songs


def top_path_segment(original: str) -> str:
    """Return the first path segment of a URL, e.g. ``/sounds/`` or ``/`` for root files.

    References:
        [PY-URLLIB-PARSE] urlsplit, https://docs.python.org/3/library/urllib.parse.html
    """
    path = urlsplit(original).path or "/"
    parts = [p for p in path.split("/") if p]
    if len(parts) <= 1 and not path.endswith("/"):
        return "/"
    return f"/{parts[0]}/" if parts else "/"


def candidate_pages(inventory: Iterable[CdxRow]) -> list[CdxRow]:
    """Select archived HTML pages whose path suggests they list songs.

    Args:
        inventory: Rows from :func:`collect_inventory`.

    Returns:
        HTML rows with a song-related word in the path, sorted by URL key.

    References:
        [PY-RE] re.search, https://docs.python.org/3/library/re.html
    """
    pages = [
        r for r in inventory
        if r.mimetype.startswith("text/html")
        and CANDIDATE_PAGE_WORDS.search(urlsplit(r.original).path)
        and audio_file(r.original) is None
    ]
    return sorted(pages, key=lambda r: r.urlkey)


def write_inventory_csv(songs: dict[str, SongSurvey], path: Path) -> None:
    """Write one CSV row per song.

    References:
        [PY-CSV] csv.writer, https://docs.python.org/3/library/csv.html
    """
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle, lineterminator="\n")
        writer.writerow([
            "slug", "formats", "directories", "has_playable_mp3", "mp3_good_captures",
            "best_mp3_timestamp", "best_mp3_original", "first_seen", "last_seen", "total_captures",
        ])
        for slug in sorted(songs):
            s = songs[slug]
            best = s.best_mp3
            writer.writerow([
                slug, " ".join(s.formats), " ".join(s.directories), "yes" if best else "no",
                len(s.good_mp3), best.timestamp if best else "", best.original if best else "",
                s.first_seen, s.last_seen, len(s.captures),
            ])


def write_candidate_pages_csv(pages: list[CdxRow], path: Path) -> None:
    """Write candidate song-listing pages to CSV.

    References:
        [PY-CSV] csv.writer, https://docs.python.org/3/library/csv.html
    """
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle, lineterminator="\n")
        writer.writerow(["canonical_url", "first_capture", "status", "wayback_url"])
        for r in pages:
            writer.writerow([canonical_url(r.original), r.timestamp, r.statuscode,
                             wayback_view_url(r.timestamp, r.original)])


def write_summary(
    songs: dict[str, SongSurvey],
    audio_rows: list[CdxRow],
    inventory: list[CdxRow],
    pages: list[CdxRow],
    legacy: list[SongSurvey],
    live_requests: int,
    path: Path,
) -> None:
    """Write the headline survey report.

    References:
        [PY-COLLECTIONS] Counter, https://docs.python.org/3/library/collections.html
        [PY-DATETIME] date.today, https://docs.python.org/3/library/datetime.html
        [IA-CDX-API] https://github.com/internetarchive/wayback/tree/master/wayback-cdx-server
    """
    playable = [s for s in songs.values() if s.best_mp3]
    no_audio = [s for s in songs.values() if s.best_mp3 is None and not s.legacy_captures]
    mime_only = [r for r in audio_rows if audio_file(r.original) is None]

    ext_counts = Counter(audio_file(r.original).ext for r in audio_rows if audio_file(r.original))
    status_counts = Counter(r.statuscode for r in audio_rows if audio_file(r.original))
    dir_counts = Counter(d for s in songs.values() for d in s.directories)
    first_year = Counter(s.first_seen[:4] for s in songs.values())
    capture_year = Counter(r.timestamp[:4] for r in audio_rows)
    top_paths = Counter(top_path_segment(r.original) for r in inventory)
    inv_mime = Counter(r.mimetype for r in inventory)
    variants = sum(1 for s in songs.values() if len({canonical_url(r.original) for r in s.captures}) < len({r.original for r in s.captures}))

    def table(counter: Counter, header: tuple[str, str], *, by_key: bool = False, top: int | None = None) -> list[str]:
        """Render a two-column Markdown table from a Counter. References: None."""
        items = sorted(counter.items()) if by_key else counter.most_common(top)
        return [f"| {header[0]} | {header[1]} |", "|---|---|", *(f"| `{k}` | {v} |" for k, v in items)]

    years = sorted(capture_year)
    lines = [
        "# Phase 1 Survey: capsteps.com in the Wayback Machine",
        "",
        f"_Generated {date.today().isoformat()} by `ingest/capsteps_ingest/survey.py` "
        f"({live_requests} live CDX requests this run; other responses came from cache)._",
        "_Sources: [IA-CDX-API], [WAYBACK-CAPSTEPS-SOUNDS], [WAYBACK-CAPSTEPS-SONGS]._",
        "",
        "## Headline numbers",
        "",
        "| Measure | Count |",
        "|---|---|",
        f"| Unique archived URLs on the domain | {len(inventory)} |",
        f"| Audio captures (all formats, all statuses) | {len(audio_rows)} |",
        f"| Songs (unique audio file slugs; each variant is its own song) | {len(songs)} |",
        f"| Songs with a playable `.mp3` capture (in scope for the site) | {len(playable)} |",
        f"| Songs with **only** legacy-format captures (see `legacy_only_songs.md`) | {len(legacy)} |",
        f"| Songs whose every capture is an error/redirect (no usable audio) | {len(no_audio)} |",
        f"| Songs captured under more than one URL spelling | {variants} |",
        f"| Audio-MIME captures without an audio extension (not grouped) | {len(mime_only)} |",
        f"| Audio capture years | {years[0] if years else '-'} – {years[-1] if years else '-'} |",
        f"| Candidate song-listing HTML pages (see `phase1_candidate_pages.csv`) | {len(pages)} |",
        "",
        "## Audio captures by format", "", *table(ext_counts, ("Extension", "Captures")), "",
        "## Audio captures by HTTP status", "",
        "`-` is a `warc/revisit` record (byte-identical to an earlier capture).", "",
        *table(status_counts, ("Status", "Captures")), "",
        "## Songs by directory", "", *table(dir_counts, ("Directory", "Songs")), "",
        "## Songs by year first archived", "", *table(first_year, ("Year", "New songs"), by_key=True), "",
        "## Audio captures by year", "", *table(capture_year, ("Year", "Captures"), by_key=True), "",
        "## Site inventory: top-level paths (top 30)", "",
        *table(top_paths, ("Path", "Unique URLs"), top=30), "",
        "## Site inventory: MIME types (top 15)", "",
        *table(inv_mime, ("MIME type", "Unique URLs"), top=15), "",
    ]
    lines += [
        "## Caveats", "",
        "- **`.ram` files are pointers, not audio.** A RealAudio `.ram` metafile holds the "
        "address of a separate `.ra`/`.rm` stream, so a status-200 `.ram` capture does not mean "
        "the audio itself was archived. This affects only the legacy-only list, since legacy "
        "formats are out of scope for the site.",
        "- **The inventory shows only each URL's first capture.** `collapse=urlkey` returns one "
        "row per URL, so a page that first returned 404 may have been archived successfully later.",
        "- **`/songs/` is absent.** No `capsteps.com/songs/` URL appears in the CDX index under any "
        "spelling; see `phase1_listing_pages.md` for the pages that actually linked to the audio.",
        "- **Junk URLs are excluded.** Audio-MIME rows without an audio extension (e.g. `...mp3&gt`, "
        "`...rae`) are crawler artifacts of malformed links, not separate songs.",
        "",
    ]
    if mime_only:
        lines += ["## Audio-MIME captures without an audio extension (first 25)", "",
                  "| Original URL | Timestamp | MIME |", "|---|---|---|",
                  *(f"| `{r.original}` | {r.timestamp} | {r.mimetype} |" for r in mime_only[:25]), ""]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    """Run the survey and write all reports.

    References:
        [PY-ARGPARSE] https://docs.python.org/3/library/argparse.html
    """
    parser = argparse.ArgumentParser(description="Phase 1 Wayback survey of capsteps.com")
    parser.add_argument("--repo-root", type=Path, default=Path(__file__).resolve().parents[2])
    args = parser.parse_args(argv)

    root: Path = args.repo_root
    reports = root / "reports"
    reports.mkdir(exist_ok=True)
    client = CdxClient(root / "ingest" / "cache" / "cdx")

    audio_rows = collect_audio_rows(client)
    inventory = collect_inventory(client)
    songs = group_songs(audio_rows)
    pages = candidate_pages(inventory)

    write_inventory_csv(songs, reports / "phase1_audio_inventory.csv")
    write_candidate_pages_csv(pages, reports / "phase1_candidate_pages.csv")
    # legacy_only_songs.md is written by build_catalog (with titles); count only here.
    legacy = [s for s in songs.values() if s.best_mp3 is None and s.legacy_captures]
    write_summary(songs, audio_rows, inventory, pages, legacy, client.live_requests,
                  reports / "phase1_survey.md")
    client.log(f"Done: {len(songs)} songs, {len(legacy)} legacy-only, {len(inventory)} unique URLs.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
