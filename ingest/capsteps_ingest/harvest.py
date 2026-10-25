"""Phase 2 harvest: download every archived capsteps.com HTML page needed for extraction.

Approved by the developer on 2026-10-25 (Phase 1 recommendations 1 and 2):

- **every distinct version** (by content digest) of the homepage (``/`` and
  ``/index.html``), because songs were featured there for only a few weeks each;
- the **latest** status-200 capture of every other archived HTML page.

One domain-wide CDX query lists every status-200 HTML capture; targets are chosen
locally, then fetched through the Wayback ``id_`` form at the polite rate. Every
response is cached in ``ingest/cache/pages/``, so the run can be interrupted and
resumed, and later stages never touch the network.

Usage:
    uv run python -m capsteps_ingest.harvest

References:
    [IA-CDX-API] filter (repeatable, ANDed), matchType=domain, digest field,
        https://github.com/internetarchive/wayback/tree/master/wayback-cdx-server
    [IA-WAYBACK-URL] ``id_`` raw-capture URL form (source still to be identified).
"""

from __future__ import annotations

import argparse
import sys
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path

from .cdx import CdxClient, CdxRow, CdxUnavailable
from .pages import validate_capture
from .urls import wayback_raw_url

DOMAIN = "capsteps.com"
HOMEPAGE_KEYS = frozenset({"com,capsteps)/", "com,capsteps)/index.html", "com,capsteps)/index.htm"})
SKIP_PREFIXES = ("/sounds/", "/images/", "/img-sys/", "/css/", "/js/", "/cgi-bin/", "/cgi-sys/",
                 "/.well-known/", "/feed", "/rss/", "/adx/")


@dataclass(frozen=True)
class Target:
    """One capture to download.

    Attributes:
        row: CDX row of the capture.
        kind: ``"homepage"`` (one per distinct digest) or ``"page"`` (latest only).

    References:
        [PY-DATACLASSES] https://docs.python.org/3/library/dataclasses.html
    """

    row: CdxRow
    kind: str


def urlkey_path(urlkey: str) -> str:
    """Return the path part of a SURT urlkey, e.g. ``com,capsteps)/radio/`` -> ``/radio/``.

    References:
        [IA-CDX-API] urlkey (SURT) format,
            https://github.com/internetarchive/wayback/tree/master/wayback-cdx-server
    """
    return urlkey.split(")", 1)[1] if ")" in urlkey else urlkey


def html_captures(client: CdxClient) -> list[CdxRow]:
    """List every status-200 HTML capture on the domain.

    References:
        [IA-CDX-API] multiple ``filter`` parameters,
            https://github.com/internetarchive/wayback/tree/master/wayback-cdx-server
    """
    client.log("Status-200 HTML captures on the domain:")
    return list(client.query(url=DOMAIN, matchType="domain",
                             filter=["statuscode:200", "mimetype:text/html"]))


def select_targets(rows: Iterable[CdxRow]) -> list[Target]:
    """Choose which captures to download.

    Homepage keys keep the earliest capture of each distinct digest; every other
    page on the main host keeps only its latest capture. Subdomains, query-string
    URLs, and asset/audio directories are skipped.

    Args:
        rows: Status-200 HTML capture rows.

    Returns:
        Targets sorted by kind, then URL key, then timestamp.

    References:
        [IA-CDX-API] digest field (identical content shares a digest),
            https://github.com/internetarchive/wayback/tree/master/wayback-cdx-server
    """
    homepage: dict[str, CdxRow] = {}
    latest: dict[str, CdxRow] = {}
    for row in rows:
        if not row.urlkey.startswith("com,capsteps)/"):
            continue  # subdomains (mail., cpanel., ...)
        path = urlkey_path(row.urlkey)
        if "?" in path or path.startswith(SKIP_PREFIXES):
            continue
        if row.urlkey in HOMEPAGE_KEYS:
            current = homepage.get(row.digest)
            if current is None or row.timestamp < current.timestamp:
                homepage[row.digest] = row
        else:
            current = latest.get(row.urlkey)
            if current is None or row.timestamp > current.timestamp:
                latest[row.urlkey] = row
    targets = [Target(r, "homepage") for r in homepage.values()]
    targets += [Target(r, "page") for r in latest.values()]
    return sorted(targets, key=lambda t: (t.kind, t.row.urlkey, t.row.timestamp))


def fetch_capture(page_client: CdxClient, row: CdxRow) -> str | None:
    """Fetch (or read from cache) one capture's original HTML.

    Returns:
        The HTML, or ``None`` if the Wayback Machine reports it missing (404/410)
        or keeps failing.

    References:
        [IA-WAYBACK-URL] ``id_`` raw-capture URL form.
    """
    try:
        return page_client.get(wayback_raw_url(row.timestamp, row.original), validate=validate_capture)
    except CdxUnavailable:
        return None


def page_client_for(root: Path, log=None) -> CdxClient:
    """Create the client used for page downloads (separate cache directory).

    References:
        None.
    """
    kwargs = {"log": log} if log else {}
    return CdxClient(root / "ingest" / "cache" / "pages", **kwargs)


def main(argv: list[str] | None = None) -> int:
    """Run the harvest, logging progress; safe to interrupt and re-run.

    References:
        [PY-ARGPARSE] https://docs.python.org/3/library/argparse.html
    """
    parser = argparse.ArgumentParser(description="Phase 2 harvest of archived capsteps.com HTML")
    parser.add_argument("--repo-root", type=Path, default=Path(__file__).resolve().parents[2])
    args = parser.parse_args(argv)
    root: Path = args.repo_root

    client = CdxClient(root / "ingest" / "cache" / "cdx")
    page_client = page_client_for(root, client.log)
    targets = select_targets(html_captures(client))
    kinds = {k: sum(1 for t in targets if t.kind == k) for k in ("homepage", "page")}
    client.log(f"Targets: {kinds['homepage']} homepage versions, {kinds['page']} other pages")

    failed = 0
    for index, target in enumerate(targets, 1):
        if fetch_capture(page_client, target.row) is None:
            failed += 1
            client.log(f"  missing: {target.row.timestamp} {target.row.original}")
        if index % 50 == 0 or index == len(targets):
            client.log(f"  {index}/{len(targets)} done ({page_client.live_requests} live, {failed} missing)")
    client.log(f"Harvest complete: {len(targets)} targets, {failed} missing.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
