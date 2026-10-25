"""Phase 1 survey of archived capsteps.com pages that link to song audio (read-only).

``capsteps.com/songs/`` has no captures in the CDX index, so this module samples
the candidate listing pages instead. It takes one status-200 capture per page per
year, downloads the original HTML through the Wayback ``id_`` form, and records
which audio files each snapshot links to and the anchor text it uses. That anchor
text is the likely source of song titles in Phase 2.

Writes:
- ``reports/phase1_listing_pages.md``  per-page, per-year link counts and structure notes
- ``reports/phase1_link_titles.csv``   slug -> anchor texts seen, with the page and capture

Usage:
    uv run python -m capsteps_ingest.pages

References:
    [IA-CDX-API] collapse=timestamp:4 (one capture per year), filter=statuscode:200,
        https://github.com/internetarchive/wayback/tree/master/wayback-cdx-server
    [IA-WAYBACK-URL] ``id_`` raw-capture URL form (source still to be identified).
    [PY-HTML-PARSER] https://docs.python.org/3/library/html.parser.html
"""

from __future__ import annotations

import argparse
import csv
import re
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urljoin

from .cdx import CdxClient, CdxRow, CdxUnavailable
from .survey import collect_audio_rows, group_songs
from .urls import AUDIO_EXTS, audio_file, wayback_raw_url, wayback_view_url

# Candidate listing pages chosen from reports/phase1_candidate_pages.csv and the
# site inventory (root/home pages and the album/sound/radio/special indexes).
CANDIDATE_PAGES = (
    "capsteps.com/",
    "capsteps.com/index.html",
    "capsteps.com/albums/",
    "capsteps.com/albums/songs.html",
    "capsteps.com/albums/scandals.html",
    "capsteps.com/albums/classics.html",
    "capsteps.com/sounds/",
    "capsteps.com/sounds/index.html",
    "capsteps.com/radio/",
    "capsteps.com/special/",
)

AUDIO_LINK_RE = re.compile(
    r"""(?:https?://[^\s"'<>]*?)?/?sounds/[^\s"'<>?#&]+?\.(?:""" + "|".join(sorted(AUDIO_EXTS)) + r")\b",
    re.I,
)
OUTAGE_MARKER = "Internet Archive: Temporarily Offline"
# Link labels that describe the file format rather than the song (observed 2026-10-25).
GENERIC_ANCHOR_RE = re.compile(
    r"format|download|stream|listen|click|here|play|promo clip|^\W*(mp3|mpeg|real ?audio|au)\W*$", re.I
)


def is_generic_anchor(text: str) -> bool:
    """True if anchor text is a format/download label rather than a song title.

    References:
        [PY-RE] re.search, https://docs.python.org/3/library/re.html
    """
    return len(text) <= 3 or bool(GENERIC_ANCHOR_RE.search(text))


def validate_capture(body: str) -> None:
    """Reject the Wayback "Temporarily Offline" page so it is retried, not cached.

    Empty bodies are accepted: some captures (e.g. ``capsteps.com/sounds/`` in
    2003) really are zero-byte status-200 responses.

    Raises:
        ValueError: If the body is the outage page.

    References:
        None (outage page text and zero-byte captures observed 2026-10-25).
    """
    if OUTAGE_MARKER in body:
        raise ValueError("Wayback outage page")


class AnchorCollector(HTMLParser):
    """Collect ``(href, text)`` pairs for every ``<a>`` element.

    References:
        [PY-HTML-PARSER] HTMLParser.handle_starttag / handle_data / handle_endtag,
            https://docs.python.org/3/library/html.parser.html
    """

    def __init__(self) -> None:
        """Initialise an empty collector. References: None."""
        super().__init__(convert_charrefs=True)
        self.anchors: list[tuple[str, str]] = []
        self.title = ""
        self._href: str | None = None
        self._text: list[str] = []
        self._in_title = False

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        """Start capturing anchor text. References: [PY-HTML-PARSER]."""
        if tag == "a":
            self._href = dict(attrs).get("href") or ""
            self._text = []
        elif tag == "title":
            self._in_title = True

    def handle_data(self, data: str) -> None:
        """Accumulate text inside an anchor or the title. References: [PY-HTML-PARSER]."""
        if self._href is not None:
            self._text.append(data)
        if self._in_title:
            self.title += data

    def handle_endtag(self, tag: str) -> None:
        """Finish an anchor or the title. References: [PY-HTML-PARSER]."""
        if tag == "a" and self._href is not None:
            self.anchors.append((self._href, " ".join("".join(self._text).split())))
            self._href = None
        elif tag == "title":
            self._in_title = False


@dataclass
class Snapshot:
    """Analysis of one archived page capture.

    References:
        [PY-DATACLASSES] https://docs.python.org/3/library/dataclasses.html
    """

    page: str
    row: CdxRow
    title: str = ""
    slugs: set[str] = field(default_factory=set)
    anchor_titles: dict[str, set[str]] = field(default_factory=dict)
    size: int = 0
    markers: list[str] = field(default_factory=list)
    error: str = ""


STRUCTURE_MARKERS = {
    "table layout": re.compile(r"<table", re.I),
    "frames": re.compile(r"<frameset|<frame\b", re.I),
    "flash/embed player": re.compile(r"<embed|<object|\.swf", re.I),
    "html5 <audio>": re.compile(r"<audio", re.I),
    "javascript audio player": re.compile(r"jplayer|soundmanager|mediaelement|playlist", re.I),
    "wordpress": re.compile(r"wp-content|wp-includes", re.I),
    "css classes for songs": re.compile(r"class=\"[^\"]*(song|track)[^\"]*\"", re.I),
}


def analyse_html(page: str, row: CdxRow, html: str) -> Snapshot:
    """Extract audio links, anchor titles, and structure markers from a capture.

    Args:
        page: Canonical page key, e.g. ``capsteps.com/``.
        row: The CDX row of the capture.
        html: Raw HTML of the capture.

    Returns:
        A populated :class:`Snapshot`.

    References:
        [PY-HTML-PARSER] https://docs.python.org/3/library/html.parser.html
        [PY-RE] re.finditer, https://docs.python.org/3/library/re.html
        [PY-URLLIB-PARSE] urljoin, https://docs.python.org/3/library/urllib.parse.html
    """
    snap = Snapshot(page=page, row=row, size=len(html))
    for match in AUDIO_LINK_RE.finditer(html):
        af = audio_file(urljoin(row.original, match.group(0)))
        if af:
            snap.slugs.add(af.slug)
    parser = AnchorCollector()
    try:
        parser.feed(html)
        parser.close()
    except Exception as exc:  # malformed 1990s HTML; keep regex results
        snap.error = f"parser: {exc}"
    snap.title = " ".join(parser.title.split())
    for href, text in parser.anchors:
        af = audio_file(urljoin(row.original, href))
        if af and text:
            snap.anchor_titles.setdefault(af.slug, set()).add(text)
            snap.slugs.add(af.slug)
    snap.markers = [name for name, rx in STRUCTURE_MARKERS.items() if rx.search(html)]
    return snap


def yearly_captures(client: CdxClient, page: str) -> list[CdxRow]:
    """Return one status-200 HTML capture per year for a page.

    References:
        [IA-CDX-API] collapse=timestamp:4, filter=statuscode:200,
            https://github.com/internetarchive/wayback/tree/master/wayback-cdx-server
    """
    return list(client.query(url=page, filter="statuscode:200", collapse="timestamp:4"))


def write_listing_report(snapshots: list[Snapshot], all_slugs: set[str], path: Path) -> None:
    """Write the per-page, per-year Markdown report with coverage numbers.

    References:
        [IA-CDX-API] https://github.com/internetarchive/wayback/tree/master/wayback-cdx-server
        [PY-DATETIME] https://docs.python.org/3/library/datetime.html
    """
    linked = set().union(*(s.slugs for s in snapshots)) if snapshots else set()
    titled = {slug for s in snapshots for slug, texts in s.anchor_titles.items()
              if any(not is_generic_anchor(t) for t in texts)}
    by_page: dict[str, list[Snapshot]] = defaultdict(list)
    for snap in snapshots:
        by_page[snap.page].append(snap)

    lines = [
        "# Phase 1: Listing pages that link to song audio",
        "",
        f"_Generated {date.today().isoformat()} by `ingest/capsteps_ingest/pages.py`. "
        "One status-200 capture per page per year, fetched via the Wayback `id_` form. "
        "Sources: [IA-CDX-API], [WAYBACK-CAPSTEPS-SOUNDS]._",
        "",
        "`capsteps.com/songs/` has **no captures** in the CDX index (checked under every URL "
        "spelling on 2026-10-25), so these pages are sampled instead.",
        "",
        "## Coverage",
        "",
        "| Measure | Count |",
        "|---|---|",
        f"| Songs (audio slugs) known from the CDX survey | {len(all_slugs)} |",
        f"| ...linked from at least one sampled snapshot | {len(linked & all_slugs)} |",
        f"| ...whose link text is a candidate title (not \"MP3 format\", \"[Download\", ...) | {len(titled & all_slugs)} |",
        f"| Audio slugs linked from pages but never archived as audio | {len(linked - all_slugs)} |",
        f"| Snapshots fetched | {len(snapshots)} ({sum(1 for s in snapshots if s.error)} with errors) |",
        "",
    ]
    for page, snaps in by_page.items():
        lines += [
            f"## `{page}`", "",
            "| Year | Capture | Page title | Audio links | Links with any text | Size (chars) | Structure | Note |",
            "|---|---|---|---|---|---|---|---|",
        ]
        for s in snaps:
            lines.append(
                f"| {s.row.timestamp[:4]} | [{s.row.timestamp}]({wayback_view_url(s.row.timestamp, s.row.original)}) "
                f"| {s.title[:60].replace('|', '/')} | {len(s.slugs)} | {len(s.anchor_titles)} | {s.size} "
                f"| {', '.join(s.markers)} | {s.error} |"
            )
        lines.append("")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_link_titles_csv(snapshots: list[Snapshot], path: Path) -> None:
    """Write every (slug, anchor text) pair seen, with where it was seen.

    References:
        [PY-CSV] csv.writer, https://docs.python.org/3/library/csv.html
    """
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(["slug", "anchor_text", "generic_label", "page", "capture_timestamp", "wayback_url"])
        rows = sorted(
            (slug, text, "yes" if is_generic_anchor(text) else "no", s.page, s.row.timestamp,
             wayback_view_url(s.row.timestamp, s.row.original))
            for s in snapshots for slug, texts in s.anchor_titles.items() for text in texts
        )
        writer.writerows(rows)


def main(argv: list[str] | None = None) -> int:
    """Run the listing-page survey.

    References:
        [PY-ARGPARSE] https://docs.python.org/3/library/argparse.html
    """
    parser = argparse.ArgumentParser(description="Phase 1 listing-page survey")
    parser.add_argument("--repo-root", type=Path, default=Path(__file__).resolve().parents[2])
    args = parser.parse_args(argv)
    root: Path = args.repo_root
    client = CdxClient(root / "ingest" / "cache" / "cdx")
    page_client = CdxClient(root / "ingest" / "cache" / "pages", log=client.log)

    all_slugs = set(group_songs(collect_audio_rows(client)))
    snapshots = []
    for page in CANDIDATE_PAGES:
        rows = [r for r in yearly_captures(client, page) if r.mimetype.startswith("text/html")]
        client.log(f"{page}: {len(rows)} yearly captures")
        for row in rows:
            url = wayback_raw_url(row.timestamp, row.original)
            try:
                html = page_client.get(url, validate=validate_capture)
            except CdxUnavailable as exc:
                snap = Snapshot(page=page, row=row, error=str(exc))
            else:
                snap = analyse_html(page, row, html)
            client.log(f"  {row.timestamp[:4]}: {len(snap.slugs)} audio links {snap.error}")
            snapshots.append(snap)

    write_listing_report(snapshots, all_slugs, root / "reports" / "phase1_listing_pages.md")
    write_link_titles_csv(snapshots, root / "reports" / "phase1_link_titles.csv")
    client.log(f"Done: {len(snapshots)} snapshots.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
