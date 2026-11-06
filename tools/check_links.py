#!/usr/bin/env python3
"""Check that the site's links still resolve: archived audio and cited sources.

For a seeded random sample of recordings (or ``--all``), requests the first byte of
the Wayback raw-audio URL the player uses and expects ``200``/``206`` with an audio
content type [IA-WAYBACK-URL] [RFC-9110]. Then requests every URL in
``references/references.yaml`` and expects a 2xx status. Requests are sequential and
spaced out, with one retry for timeouts and 5xx errors, so the Internet Archive sees
light traffic.

Network-dependent, so it is not part of the unit tests; run it by hand or on a schedule.

Usage:
    python3 tools/check_links.py                  # 20 random recordings + every reference
    python3 tools/check_links.py --sample 50 --seed 7
    python3 tools/check_links.py --all --no-references   # every recording (~15 min)

References:
    [IA-WAYBACK-URL] raw capture URLs (``id_``),
        https://en.wikipedia.org/wiki/Help:Using_the_Wayback_Machine
    [RFC-9110] Range requests and 206 Partial Content, https://www.rfc-editor.org/rfc/rfc9110
    [PY-URLLIB-REQUEST] urllib.request.urlopen, Request,
        https://docs.python.org/3/library/urllib.request.html
    [PY-RANDOM] random.Random.sample, https://docs.python.org/3/library/random.html
    [PY-JSON] https://docs.python.org/3/library/json.html
    [PY-ARGPARSE] https://docs.python.org/3/library/argparse.html
"""

from __future__ import annotations

import argparse
import json
import random
import socket
import sys
import time
import urllib.error
import urllib.request
from collections.abc import Callable
from dataclasses import dataclass

from build_bibliography import REFERENCES_FILE, REPO_ROOT, load_references

CATALOG_FILE = REPO_ROOT / "data" / "catalog.json"
# Same identification as the ingest pipeline (ingest/capsteps_ingest/cdx.py); no personal contact details.
USER_AGENT = "capitol-steps-preservation-index/0.1 (archival survey; non-commercial)"
AUDIO_TYPES = ("audio/", "application/octet-stream")

Probe = Callable[[str], tuple[int, str]]


@dataclass(frozen=True)
class Link:
    """A URL to check and what it belongs to.

    References:
        [PY-DATACLASSES] https://docs.python.org/3/library/dataclasses.html
    """

    label: str
    url: str
    audio: bool


@dataclass(frozen=True)
class Result:
    """The outcome of checking one link.

    References:
        [PY-DATACLASSES] https://docs.python.org/3/library/dataclasses.html
    """

    link: Link
    ok: bool
    detail: str


def http_probe(url: str, timeout: float = 30.0) -> tuple[int, str]:
    """Request the first byte of ``url`` and return its status and content type.

    Redirects are followed. HTTP errors are returned as their status code rather
    than raised; network errors and timeouts are raised.

    Args:
        url: Absolute URL.
        timeout: Seconds to wait for the response headers.

    Returns:
        ``(status, content_type)``; content type is ``""`` if absent.

    References:
        [PY-URLLIB-REQUEST] Request headers, urlopen, HTTPError,
            https://docs.python.org/3/library/urllib.request.html
        [RFC-9110] Range: bytes=0-0, §14.2, https://www.rfc-editor.org/rfc/rfc9110
    """
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Range": "bytes=0-0"})
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return response.status, response.headers.get("Content-Type", "")
    except urllib.error.HTTPError as error:
        return error.code, error.headers.get("Content-Type", "") if error.headers else ""


def judge(link: Link, status: int, content_type: str) -> Result:
    """Decide whether a response means the link works.

    Args:
        link: What was requested.
        status: Final HTTP status.
        content_type: The response's Content-Type header.

    Returns:
        A result; audio must be 200/206 with an audio type, anything else any 2xx.

    References:
        [RFC-9110] 200 OK and 206 Partial Content, §15.3,
            https://www.rfc-editor.org/rfc/rfc9110
    """
    detail = f"{status} {content_type}".strip()
    if link.audio:
        ok = status in (200, 206) and content_type.lower().startswith(AUDIO_TYPES)
    else:
        ok = 200 <= status < 300
    return Result(link, ok, detail)


def check(link: Link, probe: Probe, retries: int = 1, backoff: float = 5.0,
          sleep: Callable[[float], None] = time.sleep) -> Result:
    """Check one link, retrying once on a timeout, network error or 5xx.

    Args:
        link: The link.
        probe: Returns ``(status, content_type)`` or raises on network failure.
        retries: Extra attempts after a transient failure.
        backoff: Seconds to wait before a retry.
        sleep: Injected for tests.

    Returns:
        The final result.

    References:
        [PY-URLLIB-REQUEST] URLError, https://docs.python.org/3/library/urllib.request.html
    """
    for attempt in range(retries + 1):
        try:
            status, content_type = probe(link.url)
        except (urllib.error.URLError, TimeoutError, socket.timeout, ConnectionError) as error:
            result = Result(link, False, f"network error: {getattr(error, 'reason', error)}")
        else:
            result = judge(link, status, content_type)
            if result.ok or status < 500:
                return result
        if attempt < retries:
            sleep(backoff)
    return result


def catalog_links(catalog: dict, sample: int | None, seed: int) -> list[Link]:
    """The raw-audio links of a sample of recordings (all of them if ``sample`` is None).

    Args:
        catalog: Parsed ``data/catalog.json``.
        sample: How many recordings to draw, or None for every one.
        seed: Seed for the draw, so a failing sample can be re-run.

    Returns:
        Links sorted by song ID.

    References:
        [PY-RANDOM] random.Random(seed).sample, https://docs.python.org/3/library/random.html
    """
    songs = catalog["songs"]
    if sample is not None and sample < len(songs):
        songs = random.Random(seed).sample(songs, sample)
    return [Link(s["id"], s["audio"]["wayback_raw_url"], audio=True) for s in sorted(songs, key=lambda s: s["id"])]


def reference_links(entries: list[dict]) -> list[Link]:
    """One link per registered reference.

    Args:
        entries: Output of ``build_bibliography.load_references``.

    Returns:
        Links in registry order.

    References:
        None (project registry, references/references.yaml).
    """
    return [Link(f"[{e['id']}]", e["url"], audio=False) for e in entries]


def run(links: list[Link], probe: Probe, interval: float,
        sleep: Callable[[float], None] = time.sleep, out=sys.stdout) -> list[Result]:
    """Check links one at a time, printing each result as it arrives.

    Args:
        links: What to check.
        probe: See :func:`check`.
        interval: Seconds to wait between requests.
        sleep: Injected for tests.
        out: Where to print progress.

    Returns:
        One result per link, in order.

    References:
        [PY-TIME] time.sleep, https://docs.python.org/3/library/time.html
    """
    results = []
    for index, link in enumerate(links):
        if index:
            sleep(interval)
        result = check(link, probe, sleep=sleep)
        print(f"{'ok  ' if result.ok else 'FAIL'} {result.detail:<32} {link.label:<28} {link.url}", file=out, flush=True)
        results.append(result)
    return results


def main(argv: list[str] | None = None) -> int:
    """Command-line entry point.

    Args:
        argv: Argument list (defaults to ``sys.argv[1:]``).

    Returns:
        0 if every link works, 1 otherwise.

    References:
        [PY-ARGPARSE] mutually exclusive groups, BooleanOptionalAction,
            https://docs.python.org/3/library/argparse.html
        [PY-JSON] json.loads, https://docs.python.org/3/library/json.html
    """
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    which = parser.add_mutually_exclusive_group()
    which.add_argument("--sample", type=int, default=20, help="recordings to check (default 20)")
    which.add_argument("--all", action="store_true", help="check every recording")
    parser.add_argument("--seed", type=int, help="seed for the sample (default: random, printed)")
    parser.add_argument("--references", action=argparse.BooleanOptionalAction, default=True,
                        help="also check every reference URL (default: yes)")
    parser.add_argument("--interval", type=float, default=1.0, help="seconds between requests (default 1)")
    args = parser.parse_args(argv)

    seed = args.seed if args.seed is not None else random.randrange(10_000)
    catalog = json.loads(CATALOG_FILE.read_text(encoding="utf-8"))
    links = catalog_links(catalog, None if args.all else args.sample, seed)
    if args.references:
        links += reference_links(load_references(REFERENCES_FILE))
    print(f"check_links: {len(links)} links" + ("" if args.all else f" (recording sample seed {seed})"))

    results = run(links, http_probe, args.interval)
    failed = [r for r in results if not r.ok]
    print(f"check_links: {len(results) - len(failed)} ok, {len(failed)} failed")
    for result in failed:
        print(f"  {result.link.label}: {result.detail} {result.link.url}", file=sys.stderr)
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
