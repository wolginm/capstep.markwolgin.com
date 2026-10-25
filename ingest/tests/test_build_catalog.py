"""Tests for capsteps_ingest.build_catalog helpers (no network, no cache).

References:
    [PYTEST-DOCS] https://docs.pytest.org/en/stable/
"""

import pytest

from capsteps_ingest.build_catalog import (album_index, choose_title, excerpt, filename_title, notice_holder,
                                           resolve_week, song_kind)


@pytest.mark.parametrize("week,ts,expected", [
    ("January 22", "20010202083100", "2001-01-22"),
    ("December 26, 2005", "20060101091626", "2005-12-26"),
    ("December 28", "20210110030526", "2020-12-28"),   # year rolls back
    ("Dec. 5", "20111210000000", "2011-12-05"),
    ("Smarch 40", "20111210000000", ""),
])
def test_resolve_week(week, ts, expected):
    """References: [PY-DATETIME]."""
    assert resolve_week(week, ts) == expected


def test_excerpt_cuts_at_sentence():
    """Long descriptions are cut at a sentence end within the limit. References: None."""
    text = "First sentence here. " * 30
    out = excerpt(text, 100)
    assert len(out) <= 102 and out.endswith(". …")
    assert excerpt("Short.", 100) == "Short."


def test_filename_title():
    """References: None."""
    assert filename_title("campaign2012-hello") == "Campaign2012 Hello"
    assert filename_title("radio-1707") == "Radio Special, July 2017"
    assert filename_title("radio-1512-promo30") == "Radio Special Promo (30 s), December 2015"
    assert filename_title("radio-1107-promo60-arnold") == "Radio Special Promo (60 s) (Arnold), July 2011"
    assert filename_title("radio-9801") == "Radio Special, January 1998"


@pytest.mark.parametrize("slug,title,kind", [
    ("radio-0404-promo", "", "promo"), ("interview-geerges", "", "interview"), ("radio-9801", "", "radio-show"),
    ("lirty-1012", "", "lirty-dies"), ("zipper", "Old Man Zipper", "song"),
])
def test_song_kind(slug, title, kind):
    """References: None."""
    assert song_kind(slug, title) == kind


def test_notice_holder():
    """References: None."""
    assert notice_holder("Recordings and lyrics Copyright © by Newport and Eaton. (Recordings…") == "Newport and Eaton"


def test_choose_title_merges_case_variants():
    """Case/punctuation variants count together; the commonest spelling wins. References: None."""
    title, alternates = choose_title(["Putin on the Blitz", "Putin On The Blitz", "Putin On The Blitz",
                                      "Putin on a Blitz"])
    assert title == "Putin On The Blitz" and alternates == ["Putin on a Blitz"]
    assert choose_title([]) == ("", [])


def test_album_index_merges_variants_and_fills_year():
    """Regression: "&"/"and", case and leading "The" variants of one album; year from
    other sightings. References: None."""
    from capsteps_ingest.extract import Sighting
    seen = [Sighting("a", album="Sheik, Rattle and Roll"), Sighting("b", album="Sheik, Rattle & Roll", album_year="1990"),
            Sighting("c", album="Sheik, Rattle and Roll"), Sighting("d", album="Joy of Sax"),
            Sighting("e", album="The Joy of Sax", album_year="1993"), Sighting("f", album="The Joy of Sax")]
    assert set(album_index(seen).values()) == {("Sheik, Rattle and Roll", "1990"), ("The Joy of Sax", "1993")}
