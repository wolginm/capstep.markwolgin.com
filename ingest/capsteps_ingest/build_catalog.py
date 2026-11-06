"""Phase 2: build the song catalog from cached Wayback data (offline; no network).

Inputs (all from ``ingest/cache/``, filled by ``survey``, ``pages`` and ``harvest``):
audio captures from the CDX index, and archived HTML pages.

Outputs:
- ``data/catalog.json``              the site's data: one entry per playable song
- ``data/catalog.sqlite``            the same plus every sighting, for ad-hoc queries
- ``reports/legacy_only_songs.md``   songs with only legacy formats (developer review)
- ``reports/unarchived_songs.md``    songs with no usable audio capture (developer review)
- ``reports/phase2_extraction.md``   coverage and quality numbers, title conflicts

Policy (developer decisions, plan §9 and Phase 1 recommendations, 2026-10-25):
only ``.mp3`` is in scope; each variant file is its own song; titles that are never
found fall back to the file name and are flagged; album text is stored but not
yet used for grouping.

Usage:
    uv run python -m capsteps_ingest.build_catalog

References:
    [WAYBACK-CAPSTEPS-HOME] https://web.archive.org/web/*/capsteps.com/
    [WAYBACK-CAPSTEPS-SITE] https://web.archive.org/web/*/capsteps.com/*
    [WAYBACK-CAPSTEPS-SOUNDS] https://web.archive.org/cdx/search/cdx?url=capsteps.com&matchType=domain&filter=mimetype:audio.*
    [PY-JSON] https://docs.python.org/3/library/json.html
    [PY-SQLITE3] https://docs.python.org/3/library/sqlite3.html
"""

from __future__ import annotations

import argparse
import json
import re
import sqlite3
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path

from .cdx import CdxClient, CdxRow, CdxUnavailable
from .extract import Sighting, extract_copyright, extract_sightings
from .harvest import HOMEPAGE_KEYS, html_captures, select_targets
from .pages import CANDIDATE_PAGES, validate_capture, yearly_captures
from .survey import SongSurvey, collect_audio_rows, group_songs
from .urls import canonical_url, wayback_raw_url, wayback_view_url

DESCRIPTION_LIMIT = 300  # characters; descriptions are quoted briefly (plan §6)
TAKEDOWN_EMAIL = "wolginmark@gmail.com"


@dataclass(frozen=True)
class Seen:
    """A sighting together with the capture it came from.

    References:
        [PY-DATACLASSES] https://docs.python.org/3/library/dataclasses.html
    """

    sighting: Sighting
    row: CdxRow
    page: str
    notice: str


def resolve_week(week: str, capture_ts: str) -> str:
    """Turn "Week of" text into an ISO date, using the capture time for a missing year.

    Args:
        week: e.g. ``"January 22"`` or ``"March 15, 2004"`` or ``"Dec. 5"``.
        capture_ts: 14-digit capture timestamp.

    Returns:
        ``YYYY-MM-DD``, or ``""`` if the text cannot be parsed.

    References:
        [PY-DATETIME] datetime.strptime, https://docs.python.org/3/library/datetime.html
    """
    text = week.replace(".", "").strip()
    for fmt in ("%B %d, %Y", "%b %d, %Y"):
        try:
            return datetime.strptime(text, fmt).date().isoformat()
        except ValueError:
            pass
    cap = datetime.strptime(capture_ts[:8], "%Y%m%d").date()
    for fmt in ("%B %d", "%b %d"):
        try:
            parsed = datetime.strptime(f"{text} {cap.year}", f"{fmt} %Y").date()
        except ValueError:
            continue
        if parsed > cap:  # e.g. "Week of December 26" seen in a January capture
            parsed = parsed.replace(year=cap.year - 1)
        return parsed.isoformat()
    return ""


def excerpt(text: str, limit: int = DESCRIPTION_LIMIT) -> str:
    """Shorten a description to whole sentences within ``limit`` characters.

    References:
        [PY-RE] https://docs.python.org/3/library/re.html
    """
    if len(text) <= limit:
        return text
    cut = text[:limit]
    end = max(cut.rfind(". "), cut.rfind("! "), cut.rfind("? "))
    return (cut[: end + 1] if end > limit // 3 else cut.rsplit(" ", 1)[0]) + " …"


RADIO_SLUG_RE = re.compile(r"radio-(\d{2})(\d{2})(?:-promo(\d*))?(?:-(.+))?$")


def filename_title(slug: str) -> str:
    """Derive a readable fallback title from a file slug.

    Examples: ``campaign2012-hello`` -> ``"Campaign2012 Hello"``; radio files named
    ``radio-YYMM[-promoNN]`` become ``"Radio Special Promo (60 s), July 2017"``.

    References:
        [PY-DATETIME] date.strftime("%B"), https://docs.python.org/3/library/datetime.html
    """
    radio = RADIO_SLUG_RE.match(slug)
    if radio and 1 <= int(radio.group(2)) <= 12:
        yy, mm, promo, extra = radio.groups()
        when = date((1900 if int(yy) >= 90 else 2000) + int(yy), int(mm), 1).strftime("%B %Y")
        label = "Radio Special" if promo is None else f"Radio Special Promo{f' ({promo} s)' if promo else ''}"
        return f"{label}{f' ({extra.capitalize()})' if extra else ''}, {when}"
    return " ".join(word.capitalize() for word in re.split(r"[-_]+", slug) if word)


def song_kind(slug: str, title: str) -> str:
    """Classify an audio file as song, promo, interview, radio show or Lirty Dies.

    The archive mixes songs with radio promos and interviews; the site can filter
    on this. Heuristic on the slug and title.

    References:
        None (heuristic from observed slugs such as ``radio-0404-promo``).
    """
    lowered = f"{slug} {title}".lower()
    if "promo" in lowered:
        return "promo"
    if slug.startswith("interview") or "interview" in title.lower():
        return "interview"
    if re.match(r"radio-?\d", slug):
        return "radio-show"
    if slug.startswith("lirty") or title.lower().startswith("lirty dies"):
        return "lirty-dies"
    return "song"


def notice_holder(notice: str) -> str:
    """Extract the rights holder from a "Copyright © by X." notice.

    References:
        [PY-RE] https://docs.python.org/3/library/re.html
    """
    m = re.search(r"Copyright\s*©?\s*by\s+([^.()]+)", notice)
    return m.group(1).strip() if m else ""


def most_common(values: list[str]) -> str:
    """Most frequent non-empty value; ties go to the earliest. References: [PY-COLLECTIONS]."""
    values = [v for v in values if v]
    if not values:
        return ""
    counts = Counter(values)
    best = max(counts.values())
    return next(v for v in values if counts[v] == best)


def title_key(title: str) -> str:
    """Normalize a title for comparison: case, punctuation and spacing are ignored.

    References:
        [PY-RE] https://docs.python.org/3/library/re.html
    """
    return re.sub(r"[^a-z0-9]+", "", title.casefold())


def album_key(name: str) -> str:
    """Normalize an album name: like :func:`title_key`, and "&" = "and", leading "The" ignored.

    E.g. "Sheik, Rattle & Roll", "Sheik, Rattle, and Roll"; "Joy of Sax", "The Joy of Sax".

    References:
        [PY-RE] https://docs.python.org/3/library/re.html
    """
    return re.sub(r"^the(?=.)", "", title_key(name.replace("&", " and ")))


def album_index(sightings: list[Sighting]) -> dict[str, tuple[str, str]]:
    """Map each album key to its most frequent spelling and year across the whole archive.

    Many sightings name the album without a year, and a few give a different one
    (e.g. a reissue), so one archive-wide value is used for every song.

    Returns:
        ``{album_key: (spelling, year)}``; year may be ``""``.

    References:
        None.
    """
    by_key: dict[str, list[Sighting]] = defaultdict(list)
    for sighting in sightings:
        if sighting.album:
            by_key[album_key(sighting.album)].append(sighting)
    return {key: (most_common([x.album for x in group]), most_common([x.album_year for x in group]))
            for key, group in by_key.items()}


def choose_title(titles: list[str]) -> tuple[str, list[str]]:
    """Pick the most frequent title, treating case/punctuation variants as one.

    Within the winning group, the most frequent spelling wins (ties: earliest).

    Returns:
        ``(title, alternates)`` where alternates are the other distinct titles,
        one spelling per normalized group.

    References:
        [PY-COLLECTIONS] Counter, https://docs.python.org/3/library/collections.html
    """
    titles = [t for t in titles if t]
    if not titles:
        return "", []
    groups = Counter(title_key(t) for t in titles)
    best = max(groups.values())
    winner = next(title_key(t) for t in titles if groups[title_key(t)] == best)
    title = most_common([t for t in titles if title_key(t) == winner])
    alternates = sorted({most_common([t for t in titles if title_key(t) == k]) for k in groups if k != winner})
    return title, alternates


def page_key(row: CdxRow) -> str:
    """Canonical page URL without scheme, e.g. ``capsteps.com/radio/``. References: None."""
    return canonical_url(row.original)


def load_captures(cdx: CdxClient, pages: CdxClient) -> tuple[list[tuple[CdxRow, str]], int]:
    """Load every cached page capture (harvest targets plus Phase 1 yearly samples).

    Returns:
        ``([(row, html), ...], missing_count)`` with duplicates removed.

    References:
        [IA-WAYBACK-URL] ``id_`` raw-capture URL form (cache key).
    """
    rows: dict[tuple[str, str], CdxRow] = {}
    try:
        for target in select_targets(html_captures(cdx)):
            rows[(target.row.timestamp, target.row.original)] = target.row
    except CdxUnavailable:
        cdx.log("warning: harvest CDX listing not cached; using Phase 1 samples only")
    for page in CANDIDATE_PAGES:
        for row in yearly_captures(cdx, page):
            if row.mimetype.startswith("text/html"):
                rows.setdefault((row.timestamp, row.original), row)

    loaded, missing = [], 0
    for row in sorted(rows.values(), key=lambda r: r.timestamp):
        try:
            loaded.append((row, pages.get(wayback_raw_url(row.timestamp, row.original), validate=validate_capture)))
        except CdxUnavailable:
            missing += 1
    return loaded, missing


def collect_sightings(captures: list[tuple[CdxRow, str]]) -> dict[str, list[Seen]]:
    """Extract sightings from every capture, keyed by slug, oldest first.

    References:
        [WAYBACK-CAPSTEPS-HOME] https://web.archive.org/web/*/capsteps.com/
    """
    by_slug: dict[str, list[Seen]] = defaultdict(list)
    for row, html in captures:
        notice = extract_copyright(html)
        for sighting in extract_sightings(html, row.original):
            by_slug[sighting.slug].append(Seen(sighting, row, page_key(row), notice))
    return by_slug


def nearest_notice(ts: str, notices: list[tuple[str, str]]) -> tuple[str, str]:
    """Return ``(notice, timestamp)`` of the homepage notice closest in time to ``ts``.

    References:
        None.
    """
    if not notices:
        return "", ""
    return min(((n, t) for t, n in notices), key=lambda nt: abs(int(nt[1][:8]) - int(ts[:8])))


def build_song(slug: str, survey: SongSurvey, seen: list[Seen], notices: list[tuple[str, str]],
               albums: dict[str, tuple[str, str]] | None = None) -> dict:
    """Assemble one catalog entry from the audio survey and page sightings.

    Args:
        albums: Album key -> archive-wide ``(spelling, year)`` (:func:`album_index`), so
            one album is named and dated the same way on every song.

    References:
        [WAYBACK-CAPSTEPS-HOME] https://web.archive.org/web/*/capsteps.com/
        [WAYBACK-CAPSTEPS-SOUNDS] https://web.archive.org/cdx/search/cdx?url=capsteps.com&matchType=domain&filter=mimetype:audio.*
    """
    titled = [s for s in seen if s.sighting.title]
    title, alternates = choose_title([s.sighting.title for s in titled])
    title_seen = next((s for s in titled if s.sighting.title == title), None)

    key = most_common([album_key(s.sighting.album) for s in seen if s.sighting.album])
    named = [s.sighting for s in seen if s.sighting.album and album_key(s.sighting.album) == key]
    album, album_year = (albums or {}).get(key) or (most_common([s.album for s in named]),
                                                    most_common([s.album_year for s in named]))
    week_seen = next((s for s in seen if s.sighting.week), None)
    # Prefer a blurb that starts like a sentence; on pages listing several songs in one
    # paragraph the text before a later link can begin mid-sentence ("the Iran-Contra ...").
    described = [s for s in seen if s.sighting.description]
    desc_seen = next((s for s in described if not s.sighting.description[:1].islower()), described[0] if described else None)

    source = title_seen or (seen[0] if seen else None)
    notice, notice_ts = (source.notice, source.row.timestamp) if source and source.notice else ("", "")
    if not notice:
        notice, notice_ts = nearest_notice(source.row.timestamp if source else survey.first_seen, notices)

    best = survey.best_mp3
    entry = {
        "id": slug,
        "base_slug": slug.split("-", 1)[0],
        "title": title or filename_title(slug),
        "title_source": "archive" if title else "filename",
        "alternate_titles": alternates,
        "kind": song_kind(slug, title),
        "original_song": most_common([s.sighting.original_song for s in seen]),
        "album": {"title": album, "year": album_year} if album else None,
        "featured_week": resolve_week(week_seen.sighting.week, week_seen.row.timestamp) if week_seen else "",
        "first_seen_year": int(survey.first_seen[:4]),
        "description": excerpt(desc_seen.sighting.description) if desc_seen else "",
        "audio": None,
        "copyright": {
            "notice": notice,
            "holder": notice_holder(notice),
            "source_url": wayback_view_url(notice_ts, "http://www.capsteps.com/") if notice_ts else "",
        },
        "sources": [],
        "sightings": len(seen),
    }
    if best:
        entry["audio"] = {
            "original_url": best.original,
            "mimetype": best.mimetype,
            "best_timestamp": best.timestamp,
            "all_timestamps": [r.timestamp for r in survey.good_mp3],
            "wayback_raw_url": wayback_raw_url(best.timestamp, best.original),
            "wayback_view_url": wayback_view_url(best.timestamp, best.original),
        }
    cited = [s for s in (title_seen, desc_seen, week_seen) if s]
    for s in dict.fromkeys(cited):
        ref = "WAYBACK-CAPSTEPS-HOME" if s.row.urlkey in HOMEPAGE_KEYS else "WAYBACK-CAPSTEPS-SITE"
        entry["sources"].append({"ref": ref, "page": s.page, "timestamp": s.row.timestamp,
                                 "url": wayback_view_url(s.row.timestamp, s.row.original)})
    entry["sources"].append({"ref": "WAYBACK-CAPSTEPS-SOUNDS", "page": canonical_url(best.original) if best else "",
                             "timestamp": best.timestamp if best else "", "url": entry["audio"]["wayback_view_url"] if best else ""})
    return entry


def write_sqlite(path: Path, songs: list[dict], by_slug: dict[str, list[Seen]]) -> None:
    """Write songs and every sighting to SQLite for ad-hoc queries.

    References:
        [PY-SQLITE3] connect, executemany, https://docs.python.org/3/library/sqlite3.html
    """
    path.unlink(missing_ok=True)
    with sqlite3.connect(path) as db:
        db.execute("CREATE TABLE songs (id TEXT PRIMARY KEY, title TEXT, title_source TEXT, kind TEXT, "
                   "original_song TEXT, album TEXT, album_year TEXT, featured_week TEXT, first_seen_year INT, "
                   "description TEXT, audio_url TEXT, json TEXT)")
        db.execute("CREATE TABLE sightings (slug TEXT, page TEXT, timestamp TEXT, title TEXT, title_from TEXT, "
                   "original_song TEXT, album TEXT, album_year TEXT, week TEXT, description TEXT)")
        db.executemany("INSERT INTO songs VALUES (?,?,?,?,?,?,?,?,?,?,?,?)", [
            (s["id"], s["title"], s["title_source"], s["kind"], s["original_song"],
             (s["album"] or {}).get("title", ""), (s["album"] or {}).get("year", ""), s["featured_week"],
             s["first_seen_year"], s["description"], (s["audio"] or {}).get("wayback_raw_url", ""), json.dumps(s))
            for s in songs])
        db.executemany("INSERT INTO sightings VALUES (?,?,?,?,?,?,?,?,?,?)", [
            (x.sighting.slug, x.page, x.row.timestamp, x.sighting.title, x.sighting.title_from,
             x.sighting.original_song, x.sighting.album, x.sighting.album_year, x.sighting.week, x.sighting.description)
            for seen in by_slug.values() for x in seen])


def review_table(entries: list[dict], survey: dict[str, SongSurvey], legacy: bool) -> list[str]:
    """Markdown rows for a developer-review report. References: [WAYBACK-CAPSTEPS-SOUNDS]."""
    lines = ["| Song | Title | Formats | Captures (first – last) | Example capture |", "|---|---|---|---|---|"]
    for e in entries:
        s = survey[e["id"]]
        rows = s.legacy_captures if legacy else sorted(s.captures, key=lambda r: r.timestamp)
        example = rows[-1]
        title = e["title"] + (" _(from file name)_" if e["title_source"] == "filename" else "")
        lines.append(f"| `{e['id']}` | {title} | {', '.join(s.formats)} | {len(s.captures)} "
                     f"({s.first_seen[:4]} – {s.last_seen[:4]}) | [{example.timestamp[:8]} {example.statuscode}]"
                     f"({wayback_view_url(example.timestamp, example.original)}) |")
    return lines


def write_reports(root: Path, songs: list[dict], legacy: list[dict], unarchived: list[dict],
                  survey: dict[str, SongSurvey], captures: int, missing: int) -> None:
    """Write the two review reports and the extraction quality report.

    References:
        [PY-COLLECTIONS] Counter, https://docs.python.org/3/library/collections.html
        [IA-CDX-API] https://github.com/internetarchive/wayback/tree/master/wayback-cdx-server
    """
    today = date.today().isoformat()
    header = f"_Generated {today} by `ingest/capsteps_ingest/build_catalog.py`. Sources: [WAYBACK-CAPSTEPS-SOUNDS], [WAYBACK-CAPSTEPS-HOME], [WAYBACK-CAPSTEPS-SITE]._"
    (root / "reports" / "legacy_only_songs.md").write_text("\n".join([
        "# Songs available only in legacy formats", "", header, "",
        "Per the developer's decision (plan §9.4), legacy formats (`.au`, `.ra`, `.ram`, `.rm`) are **not** "
        "shown on the site. These songs have no usable `.mp3` capture and are listed here for review. "
        "Note that a `.ram` file is only a pointer to a stream, so a `.ram` capture may not contain audio.", "",
        f"**{len(legacy)} songs.**", "", *review_table(legacy, survey, legacy=True), ""]), encoding="utf-8")
    (root / "reports" / "unarchived_songs.md").write_text("\n".join([
        "# Songs with no usable audio capture", "", header, "",
        "These audio files were linked from capsteps.com, but every Wayback capture of them is an error (404) "
        "or a redirect, so there is nothing to play. They are **not** on the site (Phase 1 recommendation 4).", "",
        f"**{len(unarchived)} songs.**", "", *review_table(unarchived, survey, legacy=False), ""]), encoding="utf-8")

    n = len(songs)
    def pct(k: int) -> str:
        """Format a count with its share of all songs. References: None."""
        return f"{k} ({100 * k / n:.0f}%)" if n else "0"
    kinds = Counter(s["kind"] for s in songs)
    conflicts = [s for s in songs if s["alternate_titles"]]
    lines = [
        "# Phase 2: Extraction report", "", header, "",
        f"Pages analysed: **{captures}** archived captures ({missing} not yet cached and skipped).", "",
        "## Catalog coverage (playable songs only)", "",
        "| Field | Songs with a value |", "|---|---|",
        f"| Songs in catalog (`.mp3` playable) | {n} |",
        f"| Title found in the archive | {pct(sum(s['title_source'] == 'archive' for s in songs))} |",
        f"| Title from file name (flagged on the site) | {pct(sum(s['title_source'] == 'filename' for s in songs))} |",
        f"| Original song (parody of) | {pct(sum(bool(s['original_song']) for s in songs))} |",
        f"| Album | {pct(sum(bool(s['album']) for s in songs))} |",
        f"| Featured week | {pct(sum(bool(s['featured_week']) for s in songs))} |",
        f"| Description excerpt | {pct(sum(bool(s['description']) for s in songs))} |",
        f"| Copyright notice | {pct(sum(bool(s['copyright']['notice']) for s in songs))} |",
        "", "## Kinds", "", "| Kind | Count |", "|---|---|",
        *(f"| {k} | {v} |" for k, v in kinds.most_common()), "",
        "## Copyright notices seen", "", "| Notice | Songs |", "|---|---|",
        *(f"| {k or '_(none)_'} | {v} |" for k, v in Counter(s['copyright']['notice'] for s in songs).most_common()), "",
        f"## Songs with conflicting titles ({len(conflicts)})", "",
        "The most frequent title is used; the others are kept as `alternate_titles`.", "",
        "| Song | Chosen title | Other titles seen |", "|---|---|---|",
        *(f"| `{s['id']}` | {s['title']} | {'; '.join(s['alternate_titles'])} |" for s in conflicts), "",
        "## Songs titled from the file name", "",
        ", ".join(f"`{s['id']}`" for s in songs if s["title_source"] == "filename") or "_none_", "",
    ]
    (root / "reports" / "phase2_extraction.md").write_text("\n".join(lines), encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    """Build the catalog and reports from cache.

    References:
        [PY-ARGPARSE] https://docs.python.org/3/library/argparse.html
        [PY-JSON] json.dumps, https://docs.python.org/3/library/json.html
    """
    parser = argparse.ArgumentParser(description="Build data/catalog.json from cached Wayback data")
    parser.add_argument("--repo-root", type=Path, default=Path(__file__).resolve().parents[2])
    args = parser.parse_args(argv)
    root: Path = args.repo_root
    cdx = CdxClient(root / "ingest" / "cache" / "cdx", offline=True)
    pages = CdxClient(root / "ingest" / "cache" / "pages", offline=True, log=cdx.log)

    survey = group_songs(collect_audio_rows(cdx))
    captures, missing = load_captures(cdx, pages)
    by_slug = collect_sightings(captures)
    homepage_notices = ((row.timestamp, extract_copyright(html)) for row, html in captures
                        if row.urlkey in HOMEPAGE_KEYS)
    notices = [(ts, notice) for ts, notice in homepage_notices if notice]

    albums = album_index([x.sighting for seen in by_slug.values() for x in seen])
    entries = {slug: build_song(slug, s, by_slug.get(slug, []), notices, albums) for slug, s in survey.items()}
    songs = sorted((e for e in entries.values() if e["audio"]), key=lambda e: e["id"])
    legacy = sorted((e for s, e in entries.items() if not e["audio"] and survey[s].legacy_captures), key=lambda e: e["id"])
    unarchived = sorted((e for s, e in entries.items() if not e["audio"] and not survey[s].legacy_captures),
                        key=lambda e: e["id"])

    data = root / "data"
    data.mkdir(exist_ok=True)
    catalog = {
        "generated": date.today().isoformat(),
        "description": "Unofficial index of Capitol Steps audio archived by the Internet Archive Wayback Machine.",
        "takedown_email": TAKEDOWN_EMAIL,
        "references": ["WAYBACK-CAPSTEPS-HOME", "WAYBACK-CAPSTEPS-SITE", "WAYBACK-CAPSTEPS-SOUNDS", "IA-CDX-API"],
        "counts": {"songs": len(songs), "legacy_only_excluded": len(legacy), "unarchived_excluded": len(unarchived)},
        "songs": songs,
    }
    (data / "catalog.json").write_text(json.dumps(catalog, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    write_sqlite(data / "catalog.sqlite", songs, by_slug)
    write_reports(root, songs, legacy, unarchived, survey, len(captures), missing)
    cdx.log(f"Catalog: {len(songs)} songs; {len(legacy)} legacy-only, {len(unarchived)} unarchived; "
            f"{len(captures)} pages analysed, {missing} not cached.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
