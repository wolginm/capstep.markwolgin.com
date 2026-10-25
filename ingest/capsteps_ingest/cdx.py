"""Polite, cached client for the Internet Archive Wayback CDX Server API.

The CDX API is slow and intermittently returns "Temporarily Offline" pages, so
this client throttles requests, retries with exponential backoff, pages through
large result sets with resume keys, and caches every raw response on disk so a
re-run never repeats a request that already succeeded.

References:
    [IA-CDX-API] Wayback CDX Server API (url, matchType, filter, collapse,
        output=json, limit, showResumeKey/resumeKey),
        https://github.com/internetarchive/wayback/tree/master/wayback-cdx-server
    [PY-URLLIB-REQUEST] Python docs, urllib.request,
        https://docs.python.org/3/library/urllib.request.html
"""

from __future__ import annotations

import hashlib
import json
import sys
import time
import urllib.error
import urllib.request
from collections.abc import Callable, Iterator
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlencode

CDX_ENDPOINT = "https://web.archive.org/cdx/search/cdx"
USER_AGENT = "capitol-steps-preservation-index/0.1 (archival survey; non-commercial)"
FIELDS = ("urlkey", "timestamp", "original", "mimetype", "statuscode", "digest", "length")

Fetcher = Callable[[str], str]


class CdxUnavailable(RuntimeError):
    """Raised when the CDX API keeps failing after every retry.

    References:
        None.
    """


@dataclass(frozen=True)
class CdxRow:
    """One capture record from the CDX index.

    Attributes:
        urlkey: SURT-form canonical key (scheme, ``www.`` and default port removed).
        timestamp: 14-digit capture time, ``YYYYMMDDhhmmss``.
        original: URL exactly as it was crawled.
        mimetype: MIME type reported at crawl time (``warc/revisit`` for duplicates).
        statuscode: HTTP status as a string (``-`` for revisit records).
        digest: SHA-1 (base32) of the response body.
        length: Compressed record length in bytes, as a string.

    References:
        [IA-CDX-API] Default field list and urlkey semantics,
            https://github.com/internetarchive/wayback/tree/master/wayback-cdx-server
    """

    urlkey: str
    timestamp: str
    original: str
    mimetype: str
    statuscode: str
    digest: str
    length: str

    @property
    def year(self) -> int:
        """Capture year parsed from the timestamp.

        References:
            [IA-CDX-API] timestamp format,
                https://github.com/internetarchive/wayback/tree/master/wayback-cdx-server
        """
        return int(self.timestamp[:4])


def parse_json_page(text: str) -> tuple[list[CdxRow], str | None]:
    """Parse one ``output=json`` CDX response page.

    With ``showResumeKey=true`` the API appends an empty row followed by a
    one-element row holding the resume key when more results remain.

    Args:
        text: Raw response body.

    Returns:
        ``(rows, resume_key)``; ``resume_key`` is ``None`` on the last page.

    Raises:
        ValueError: If the body is not CDX JSON (e.g. an HTML outage page).

    References:
        [IA-CDX-API] output=json and showResumeKey behaviour,
            https://github.com/internetarchive/wayback/tree/master/wayback-cdx-server
        [PY-JSON] json.loads, https://docs.python.org/3/library/json.html
    """
    stripped = text.strip()
    if not stripped:
        return [], None
    try:
        data = json.loads(stripped)
    except json.JSONDecodeError as exc:
        raise ValueError(f"not CDX JSON: {stripped[:80]!r}") from exc
    if not isinstance(data, list):
        raise ValueError("CDX JSON is not a list")

    resume_key = None
    if len(data) >= 2 and data[-2] == [] and len(data[-1]) == 1:
        resume_key = data[-1][0]
        data = data[:-2]

    if not data:
        return [], resume_key
    header, *body = data
    index = {name: header.index(name) for name in FIELDS if name in header}
    rows = [
        CdxRow(**{name: (row[index[name]] if name in index else "") for name in FIELDS})
        for row in body
        if row
    ]
    return rows, resume_key


def urllib_fetch(url: str, timeout: float = 300.0) -> str:
    """Fetch a URL with the project User-Agent and return the decoded body.

    Args:
        url: Absolute URL.
        timeout: Socket timeout in seconds.

    Returns:
        Response body decoded as UTF-8 (undecodable bytes replaced).

    References:
        [PY-URLLIB-REQUEST] urllib.request.Request / urlopen,
            https://docs.python.org/3/library/urllib.request.html
    """
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return response.read().decode("utf-8", errors="replace")


class CdxClient:
    """Throttled, retrying, disk-caching CDX client.

    References:
        [IA-CDX-API] https://github.com/internetarchive/wayback/tree/master/wayback-cdx-server
        [PY-TIME] time.monotonic / time.sleep, https://docs.python.org/3/library/time.html
        [PY-HASHLIB] hashlib.sha256 for cache keys,
            https://docs.python.org/3/library/hashlib.html
    """

    def __init__(
        self,
        cache_dir: Path,
        *,
        fetch: Fetcher = urllib_fetch,
        min_interval: float = 5.0,
        max_retries: int = 6,
        backoff_base: float = 15.0,
        page_size: int = 5000,
        sleep: Callable[[float], None] = time.sleep,
        log: Callable[[str], None] = lambda msg: print(msg, file=sys.stderr),
    ) -> None:
        """Create a client.

        Args:
            cache_dir: Directory for raw response files (created if missing).
            fetch: Function that GETs a URL and returns its body.
            min_interval: Minimum seconds between live requests.
            max_retries: Retries per request before giving up.
            backoff_base: First retry delay in seconds; doubles each retry.
            page_size: ``limit`` per request when paging with resume keys.
            sleep: Sleep function (injectable for tests).
            log: Progress logger.

        References:
            None (constructor; behaviour documented on the class).
        """
        self.cache_dir = cache_dir
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self._fetch = fetch
        self.min_interval = min_interval
        self.max_retries = max_retries
        self.backoff_base = backoff_base
        self.page_size = page_size
        self._sleep = sleep
        self.log = log
        self._last_request = 0.0
        self.live_requests = 0

    def _cache_path(self, url: str) -> Path:
        """Return the cache file path for a request URL.

        References:
            [PY-HASHLIB] hashlib.sha256, https://docs.python.org/3/library/hashlib.html
        """
        return self.cache_dir / f"{hashlib.sha256(url.encode()).hexdigest()}.json"

    def get(self, url: str, validate: Callable[[str], object] = parse_json_page) -> str:
        """GET a Wayback URL, using the cache, throttle, and retry policy.

        Only responses that pass ``validate`` are cached, so outage pages are
        retried rather than stored. HTTP 404/410 is permanent and not retried.

        Args:
            url: Full request URL (CDX query or archived capture).
            validate: Raises ``ValueError`` if the body is unusable. Defaults to
                CDX JSON validation.

        Returns:
            Raw response body.

        Raises:
            CdxUnavailable: If every retry fails.

        References:
            [PY-TIME] time.monotonic, https://docs.python.org/3/library/time.html
            [PY-URLLIB-REQUEST] urllib.error.HTTPError / URLError,
                https://docs.python.org/3/library/urllib.request.html
        """
        cache_file = self._cache_path(url)
        if cache_file.exists():
            return cache_file.read_text(encoding="utf-8")

        delay = self.backoff_base
        last_error: Exception | None = None
        for attempt in range(self.max_retries + 1):
            wait = self.min_interval - (time.monotonic() - self._last_request)
            if wait > 0:
                self._sleep(wait)
            self._last_request = time.monotonic()
            self.live_requests += 1
            try:
                body = self._fetch(url)
                validate(body)  # raises ValueError on outage HTML
            except urllib.error.HTTPError as exc:
                if exc.code in (404, 410):
                    raise CdxUnavailable(f"HTTP {exc.code}: {url}") from exc
                last_error = exc
                if attempt == self.max_retries:
                    break
                self.log(f"  attempt {attempt + 1} failed ({exc}); retrying in {delay:.0f}s")
                self._sleep(delay)
                delay *= 2
                continue
            except (urllib.error.URLError, TimeoutError, OSError, ValueError) as exc:
                last_error = exc
                if attempt == self.max_retries:
                    break
                self.log(f"  attempt {attempt + 1} failed ({exc}); retrying in {delay:.0f}s")
                self._sleep(delay)
                delay *= 2
                continue
            cache_file.write_text(body, encoding="utf-8")
            return body
        raise CdxUnavailable(f"CDX request failed after retries: {url}") from last_error

    def query(self, **params: str) -> Iterator[CdxRow]:
        """Yield every row for a CDX query, following resume keys.

        Args:
            **params: CDX query parameters (``url``, ``matchType``, ``filter``,
                ``collapse``, ...). ``output``, ``limit`` and ``showResumeKey``
                are set by this method.

        Yields:
            :class:`CdxRow` objects in index order.

        References:
            [IA-CDX-API] Pagination via showResumeKey/resumeKey,
                https://github.com/internetarchive/wayback/tree/master/wayback-cdx-server
            [PY-URLLIB-PARSE] urlencode, https://docs.python.org/3/library/urllib.parse.html
        """
        base = {**params, "output": "json", "limit": str(self.page_size), "showResumeKey": "true"}
        resume_key: str | None = None
        page = 0
        while True:
            request_params = dict(base)
            if resume_key:
                request_params["resumeKey"] = resume_key
            url = f"{CDX_ENDPOINT}?{urlencode(request_params)}"
            rows, resume_key = parse_json_page(self.get(url))
            page += 1
            self.log(f"  page {page}: {len(rows)} rows" + (" (more)" if resume_key else ""))
            yield from rows
            if not resume_key:
                return
