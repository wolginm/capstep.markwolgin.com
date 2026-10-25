"""Tests for capsteps_ingest.pages HTML analysis (no network).

References:
    [PYTEST-DOCS] https://docs.pytest.org/en/stable/
    [PY-HTML-PARSER] https://docs.python.org/3/library/html.parser.html
"""

import pytest

from capsteps_ingest.cdx import CdxRow
from capsteps_ingest.pages import analyse_html, is_generic_anchor, validate_capture

ROW = CdxRow("com,capsteps)/", "20060101000000", "http://www.capsteps.com:80/", "text/html", "200", "D", "1")

HTML = """<html><head><title>Capitol Steps  Home</title></head><body><table>
<a href="/sounds/401k.mp3">401K &amp; Me</a>
<a href="sounds/aberdeen.RAM"><b>Aberdeen</b></a>
<a href="http://www.capsteps.com/sounds/obamamia.mp3"><img src="x.gif"></a>
<script>play('/sounds/jsonly-song.mp3')</script>
<a href="/albums/">Albums</a>
</table></body></html>"""


def test_analyse_html_finds_links_titles_and_markers():
    """Anchors, relative links, JS-only links, and markers are all found. References: None."""
    snap = analyse_html("capsteps.com/", ROW, HTML)
    assert snap.title == "Capitol Steps Home"
    assert snap.slugs == {"401k", "aberdeen", "obamamia", "jsonly-song"}
    assert snap.anchor_titles == {"401k": {"401K & Me"}, "aberdeen": {"Aberdeen"}}
    assert "table layout" in snap.markers


def test_validate_capture_rejects_outage():
    """The outage page is rejected so it is retried, not cached. References: None."""
    with pytest.raises(ValueError):
        validate_capture("<title>Internet Archive: Temporarily Offline</title>")


@pytest.mark.parametrize("body", ["", "<html></html>"])
def test_validate_capture_accepts_empty_and_normal(body):
    """Zero-byte captures are real (observed 2026-10-25) and must be accepted. References: None."""
    validate_capture(body)


@pytest.mark.parametrize("text,generic", [
    ("MP3 format", True), ("[Download", True), ("Streaming]", True), ("RealAudio/RA format", True),
    ("promo clip", True), ("Modern Major Liberal", False), ("Buy, Buy, American Pie", False),
])
def test_is_generic_anchor(text, generic):
    """Format/download labels are generic; song titles are not (observed labels). References: None."""
    assert is_generic_anchor(text) is generic
