"""Tests for tools/check_links.py (no network: the probe is faked).

References:
    [PYTEST-DOCS] https://docs.pytest.org/en/stable/
"""

import io
import urllib.error

import pytest

from check_links import Link, catalog_links, check, judge, reference_links, run

AUDIO = Link("noriega", "https://web.archive.org/web/20210213225452id_/https://www.capsteps.com/sounds/noriega.mp3", True)
PAGE = Link("[RFC-9110]", "https://www.rfc-editor.org/rfc/rfc9110", False)


def fake(*responses):
    """Probe that returns or raises the given responses in order, recording calls. References: None."""
    calls = []
    queue = list(responses)

    def probe(url):
        """Record the URL and return or raise the next response. References: None."""
        calls.append(url)
        item = queue.pop(0)
        if isinstance(item, Exception):
            raise item
        return item

    return probe, calls


@pytest.mark.parametrize(
    ("link", "status", "content_type", "ok"),
    [
        (AUDIO, 206, "audio/mpeg", True),
        (AUDIO, 200, "audio/mpeg", True),
        (AUDIO, 200, "application/octet-stream", True),
        (AUDIO, 200, "text/html; charset=utf-8", False),  # a Wayback error page, not the recording
        (AUDIO, 404, "audio/mpeg", False),
        (PAGE, 200, "text/html", True),
        (PAGE, 206, "text/html", True),
        (PAGE, 403, "text/html", False),
    ],
)
def test_judge(link, status, content_type, ok):
    """Audio needs 200/206 and an audio type; pages need any 2xx. References: [RFC-9110]."""
    assert judge(link, status, content_type).ok is ok


def test_check_retries_transient_failures_once():
    """Timeouts and 5xx are retried once after a pause; 4xx is not. References: None."""
    sleeps = []
    probe, calls = fake(urllib.error.URLError("timed out"), (206, "audio/mpeg"))
    assert check(AUDIO, probe, sleep=sleeps.append).ok
    assert len(calls) == 2 and sleeps == [5.0]

    probe, calls = fake((503, "text/html"), (503, "text/html"))
    result = check(PAGE, probe, sleep=lambda _: None)
    assert not result.ok and result.detail == "503 text/html" and len(calls) == 2

    probe, calls = fake((404, "text/html"))
    assert not check(PAGE, probe, sleep=lambda _: None).ok and len(calls) == 1


def test_catalog_sample_is_seeded_and_uses_the_player_url():
    """The same seed draws the same recordings; links are the raw audio URLs. References: [PY-RANDOM]."""
    catalog = {"songs": [{"id": f"s{i}", "audio": {"wayback_raw_url": f"https://web.archive.org/web/1id_/{i}.mp3"}}
                         for i in range(10)]}
    first = catalog_links(catalog, 3, seed=1)
    assert first == catalog_links(catalog, 3, seed=1)
    assert len(first) == 3 and all(link.audio and "id_/" in link.url for link in first)
    assert len(catalog_links(catalog, None, seed=1)) == 10


def test_run_paces_requests_and_reports_each_link():
    """Requests are spaced by the interval and every result is printed. References: [PY-TIME]."""
    sleeps, out = [], io.StringIO()
    probe, _ = fake((206, "audio/mpeg"), (404, "text/html"))
    results = run([AUDIO, PAGE], probe, interval=1.0, sleep=sleeps.append, out=out)
    assert [r.ok for r in results] == [True, False]
    assert sleeps == [1.0]
    assert out.getvalue().splitlines()[1].startswith("FAIL 404 text/html")


def test_reference_links():
    """Each registry entry becomes one non-audio link labelled by its ID. References: None."""
    assert reference_links([{"id": "RFC-9110", "url": PAGE.url}]) == [PAGE]
