"""Tests for capsteps_ingest.cdx using a fake fetcher (no network).

References:
    [PYTEST-DOCS] tmp_path fixture, https://docs.pytest.org/en/stable/
    [IA-CDX-API] output=json + showResumeKey response shape,
        https://github.com/internetarchive/wayback/tree/master/wayback-cdx-server
"""

import json

import pytest

from capsteps_ingest.cdx import CdxClient, CdxUnavailable, parse_json_page

HEADER = ["urlkey", "timestamp", "original", "mimetype", "statuscode", "digest", "length"]
ROW = ["com,capsteps)/sounds/401k.mp3", "20050827124146", "http://www.capsteps.com/sounds/401k.mp3",
       "audio/x-mpeg", "200", "ABC", "123"]
OUTAGE_HTML = "<html><head><title>Internet Archive: Temporarily Offline</title></head></html>"


def page(rows, resume=None):
    """Build a CDX JSON page. References: [IA-CDX-API]."""
    data = [HEADER, *rows]
    if resume:
        data += [[], [resume]]
    return json.dumps(data)


def make_client(tmp_path, responses):
    """Client whose fetcher pops canned responses; exceptions are raised. References: None."""
    calls = []

    def fetch(url):
        calls.append(url)
        item = responses.pop(0)
        if isinstance(item, Exception):
            raise item
        return item

    client = CdxClient(tmp_path, fetch=fetch, min_interval=0, backoff_base=0, max_retries=2,
                       sleep=lambda s: None, log=lambda m: None)
    return client, calls


def test_parse_json_page_with_resume_key():
    """Resume key is split off the trailing rows (observed format, 2026-10-25). References: [IA-CDX-API]."""
    rows, key = parse_json_page(page([ROW], resume="eJxLzs"))
    assert key == "eJxLzs"
    assert len(rows) == 1 and rows[0].statuscode == "200" and rows[0].year == 2005


def test_parse_json_page_empty_body():
    """An empty body (no matches) yields no rows. References: [IA-CDX-API]."""
    assert parse_json_page("") == ([], None)


def test_parse_json_page_rejects_outage_html():
    """The 'Temporarily Offline' page is not mistaken for data. References: None."""
    with pytest.raises(ValueError):
        parse_json_page(OUTAGE_HTML)


def test_query_follows_resume_keys(tmp_path):
    """query() requests the next page with resumeKey until none remains. References: [IA-CDX-API]."""
    row2 = [*ROW[:1], "20130219052302", *ROW[2:]]
    client, calls = make_client(tmp_path, [page([ROW], resume="K1"), page([row2])])
    rows = list(client.query(url="capsteps.com", matchType="domain"))
    assert [r.timestamp for r in rows] == ["20050827124146", "20130219052302"]
    assert "resumeKey=K1" in calls[1]


def test_get_retries_outage_then_caches(tmp_path):
    """Outage pages and errors are retried; only the good body is cached. References: None."""
    client, calls = make_client(tmp_path, [OUTAGE_HTML, OSError("reset"), page([ROW])])
    url = "https://web.archive.org/cdx/search/cdx?url=x"
    assert client.get(url) == page([ROW])
    assert len(calls) == 3
    # Second call is served from disk cache, no fetch.
    assert client.get(url) == page([ROW]) and len(calls) == 3


def test_get_gives_up_after_max_retries(tmp_path):
    """Persistent failure raises CdxUnavailable and caches nothing. References: None."""
    client, _ = make_client(tmp_path, [OUTAGE_HTML] * 3)
    with pytest.raises(CdxUnavailable):
        client.get("https://web.archive.org/cdx/search/cdx?url=y")
    assert not list(tmp_path.iterdir())
