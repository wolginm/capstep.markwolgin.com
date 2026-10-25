"""Tests for capsteps_ingest.survey grouping logic (no network).

References:
    [PYTEST-DOCS] https://docs.pytest.org/en/stable/
"""

from capsteps_ingest.cdx import CdxRow
from capsteps_ingest.survey import group_songs, top_path_segment


def row(original, ts="20050101000000", status="200", mime="audio/mpeg"):
    """Build a CdxRow for tests. References: None."""
    return CdxRow("k", ts, original, mime, status, "D", "1")


def test_group_songs_variants_are_separate_and_spellings_merge():
    """Variants are separate songs; URL spellings of one file merge. References: None."""
    songs = group_songs([
        row("http://www.capsteps.com:80/sounds/401k.mp3"),
        row("https://capsteps.com/sounds/401k.mp3", ts="20130101000000"),
        row("http://www.capsteps.com/sounds/401k.ram"),
        row("http://www.capsteps.com/sounds/401k-obamamia.mp3"),
    ])
    assert sorted(songs) == ["401k", "401k-obamamia"]
    assert songs["401k"].formats == ["mp3", "ram"]
    assert songs["401k"].best_mp3.timestamp == "20130101000000"


def test_best_mp3_ignores_error_captures_and_flags_legacy_only():
    """A 404-only mp3 is not playable; the song falls back to legacy. References: None."""
    songs = group_songs([
        row("http://www.capsteps.com/sounds/aberdeen.mp3", status="404", mime="text/html"),
        row("http://www.capsteps.com/sounds/aberdeen.au", mime="audio/basic"),
    ])
    s = songs["aberdeen"]
    assert s.best_mp3 is None and s.has_any_mp3_url and len(s.legacy_captures) == 1


def test_top_path_segment():
    """Root files map to '/', others to their first directory. References: None."""
    assert top_path_segment("http://www.capsteps.com/sounds/a.mp3") == "/sounds/"
    assert top_path_segment("http://www.capsteps.com/index.html") == "/"
    assert top_path_segment("http://www.capsteps.com/") == "/"
