"""Tests for capsteps_ingest.urls.

References:
    [PYTEST-DOCS] https://docs.pytest.org/en/stable/
    [WAYBACK-CAPSTEPS-SOUNDS] sample URLs taken from the 2026-10-25 CDX probe,
        https://web.archive.org/cdx/search/cdx?url=capsteps.com&matchType=domain&filter=mimetype:audio.*
"""

import pytest

from capsteps_ingest.urls import audio_file, canonical_url, wayback_raw_url


@pytest.mark.parametrize(
    "original",
    [
        "http://www.capsteps.com:80/sounds/401k.mp3",
        "https://www.capsteps.com/sounds/401k.mp3",
        "http://capsteps.com/sounds/401k.mp3",
        "HTTP://WWW.CAPSTEPS.COM:80/sounds/401k.mp3",
        "https://capsteps.com:443/sounds/401k.mp3#frag",
    ],
)
def test_canonical_url_collapses_spelling_variants(original):
    """All recorded spellings of one file normalize to the same key. References: None."""
    assert canonical_url(original) == "capsteps.com/sounds/401k.mp3"


def test_canonical_url_keeps_path_case_and_nondefault_port():
    """Paths stay case-sensitive; non-default ports are kept. References: [RFC-3986]."""
    assert canonical_url("http://www.capsteps.com:8080/Sounds/A.mp3") == "capsteps.com:8080/Sounds/A.mp3"


def test_audio_file_parses_variant_slug():
    """Variant files keep their full slug (each variant is its own song). References: None."""
    af = audio_file("http://www.capsteps.com/sounds/401k-obamamia.mp3")
    assert af is not None
    assert (af.slug, af.ext, af.directory) == ("401k-obamamia", "mp3", "/sounds/")


def test_audio_file_lowercases_ext_and_slug():
    """Extension and slug are case-folded for grouping. References: None."""
    af = audio_file("http://www.capsteps.com:80/sounds/Aberdeen.RAM")
    assert af is not None and (af.slug, af.ext) == ("aberdeen", "ram")


@pytest.mark.parametrize("original", ["http://www.capsteps.com/songs/", "http://www.capsteps.com/sounds/x.html",
                                      "http://www.capsteps.com/sounds/.mp3"])
def test_audio_file_rejects_non_audio(original):
    """Non-audio URLs return None. References: None."""
    assert audio_file(original) is None


def test_wayback_raw_url():
    """Raw-bytes URL uses the id_ flag. References: [IA-WAYBACK-URL]."""
    assert (wayback_raw_url("20130219052302", "http://www.capsteps.com/sounds/401k.mp3")
            == "https://web.archive.org/web/20130219052302id_/http://www.capsteps.com/sounds/401k.mp3")
