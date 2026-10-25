"""Extract song details from archived capsteps.com HTML.

From 1996 to 2021 the site presented each featured song the same basic way
(observed in captures of ``capsteps.com/``, Phase 1, 2026-10-25):

- items are separated by ``<hr>``;
- an optional ``Week of <date>`` line, then a topical description paragraph;
- the song title: the audio link's own text (2011 on) or, when the link text
  is a format label like "MP3 format" (1996–2010), the **bold** text next to the
  format links;
- the original song being parodied in square brackets: ``[ Old Man River ]``;
- optionally ``From the album <Album> (<year>)``.

The page is first flattened into a marked-up text stream (bold runs, audio links,
and ``<hr>`` boundaries are kept as markers), and the rules above are applied to
the stream with regular expressions.

References:
    [WAYBACK-CAPSTEPS-HOME] Archived capsteps.com homepage captures (structure observed),
        https://web.archive.org/web/2006*/capsteps.com/
    [PY-HTML-PARSER] https://docs.python.org/3/library/html.parser.html
    [PY-RE] https://docs.python.org/3/library/re.html
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from html import unescape
from html.parser import HTMLParser
from urllib.parse import urljoin

from .urls import audio_file

HR = "\u27e6HR\u27e7"
B_OPEN, CLOSE = "\u27e6B:", "\u27e7"
A_OPEN = "\u27e6A:"

ANCHOR_RE = re.compile("\u27e6A:([^|\u27e7]+)\\|([^|\u27e7]+)\\|([^\u27e7]*)\u27e7")
BOLD_RE = re.compile("\u27e6B:([^\u27e7]*)\u27e7")
MARKER_RE = re.compile("\u27e6[^\u27e7]*\u27e7")
BRACKET_RE = re.compile(r"\[([^\[\]\u27e6\u27e7]{2,160})\]")
WEEK_RE = re.compile(r"Week of ([A-Z][a-z]{2,8}\.? \d{1,2}(?:, \d{4})?)")
ALBUM_RE = re.compile(
    r"(?:From (?:the|our|their)?\s*(?:[\w-]+\s+){0,2}?(?:album|CD)|Get the album)\b[:\s]*(.{2,80}?)\s*"
    r"(?:\((\d{4})\)|\.\s|\.?\s*$|\u27e6|\s[\u2014-]\s)",
    re.I,
)
# Footer notices, e.g. "Recordings and lyrics Copyright © by Newport and Eaton.
# (Recordings and lyrics prior to 2007 Copyright © by Strauss, Newport & Eaton or by
# Strauss & Newport. This work includes parodies of the original songs. All rights
# reserved, ... These audio files are provided for individual listening only. Do not
# redistribute." The parenthetical is often never closed, so each sentence is matched
# separately and kept in page order.
NOTICE_RES = (
    re.compile(r"Recordings and lyrics Copyright[^.()]*\."),
    re.compile(r"\(?Recordings and lyrics prior to \d{4} Copyright[^.()]*\.\)?"),
    re.compile(r"This work includes parodies of the original songs[^.]*\.", re.I),
    re.compile(r"All rights reserved[^.]*\.", re.I),
    re.compile(r"These audio files are provided for individual listening only\.(?:\s*Do not redistribute\.)?", re.I),
)
# Link labels that name a file format or action rather than a song. Whole-label
# matches only (one or more of these words, e.g. "RA Streaming"), so real titles
# containing "Here" or "Play" are not rejected.
GENERIC_WORD = (r"(?:download|streaming|click here|here|listen(?: here| in)?|play|mp3|mpeg|real ?audio"
                r"|au|ra|wav|interview(?:ed)?)")
GENERIC_RE = re.compile(rf"\bformat\b|promo clip|^\W*{GENERIC_WORD}(?:\W+{GENERIC_WORD})*\W*$", re.I)
# A format note appended to a title, e.g. "Pack the Knife (MP3)" (capture 20060810061657).
FORMAT_SUFFIX_RE = re.compile(r"\s*\((?:mp3|real ?audio|ra|au|wav)\b[^)]*\)\s*$", re.I)
# Words that continue a sentence after a link, e.g. "the Bush tax cut rates" (20070425204618).
# "and"/"or" are excluded: titles appear in lists, e.g. "Hear the saga of Enron - ron and
# other great hits" (20020721222416), "Do You Fear What I Fear? and many more" (20070104010002).
PROSE_AFTER_RE = re.compile(r"\s*(?!(?:and|or)\b)[a-z]")
# An article right before a link also marks prose: "such as the Wedtech scandal" (20191015204704).
PROSE_BEFORE_RE = re.compile(r"\b(?:the|a|an)\s*$")
# Bracketed site prompts that are not a parodied song, e.g. "[ Read more Lirty Dies or
# download from iTunes ]" (Lirty Dies pages, 2010-2019).
NOT_ORIGINAL_RE = re.compile(r"\b(?:download|transcript|iTunes|read (?:the|these|this|more|other|and)|(?:see|hear) more)\b",
                             re.I)
JUNK_RE = re.compile(
    r"Vol\.\s*\d+,\s*No\.\s*\d+|-->|\*|We put the MOCK in Democracy!?"
    r"|Sign up for our mailing list[^.]*\.",
    re.I,
)

BOLD_TAGS = {"b", "strong", "h1", "h2", "h3", "h4", "h5", "h6"}
BREAK_TAGS = {"br", "p", "div", "td", "tr", "li", "center", "table", "ul", "ol", "dd", "dt", "h5"}
SKIP_TAGS = {"script", "style", "noscript", "title"}
# Containers skipped whole: the 2008-2021 site menu, <div id="navigation"> (capture 20170711104555).
SKIP_IDS = {"navigation"}
VOID_TAGS = {"br", "hr", "img", "input", "meta", "link", "area", "base", "col", "wbr", "source"}
TITLE_WINDOW = 160  # chars searched beside an audio link group for a bold title


def is_generic(text: str) -> bool:
    """True if text is a format/download label, not a title.

    References:
        [PY-RE] https://docs.python.org/3/library/re.html
    """
    text = text.strip()
    return len(text) <= 2 or bool(GENERIC_RE.search(text))


def looks_like_title(text: str) -> bool:
    """True if text starts like a title: a capital, a digit, or an "iPod"-style word.

    Lower-case starts are prose, e.g. bold "podcast" or link "pre-Games bribery parody".

    References:
        [PY-RE] https://docs.python.org/3/library/re.html
    """
    return text[:1].isupper() or text[:1].isdigit() or bool(re.match(r"i[A-Z]", text))


def clean(text: str) -> str:
    """Strip markers (keeping bold text), collapse whitespace, trim punctuation debris.

    References:
        [PY-RE] https://docs.python.org/3/library/re.html
    """
    text = BOLD_RE.sub(lambda m: f" {m.group(1)} ", text)
    text = MARKER_RE.sub(" ", text)
    text = re.sub(r"\s+([,;!?]|\.(?!\.))", r"\1", " ".join(text.split()))  # "TAX TIME , and" -> "TAX TIME, and"
    return text.strip(" |[]-:,")


def fix_drop_cap(text: str) -> str:
    """Rejoin a split drop-cap first letter, e.g. ``"W ho was"`` -> ``"Who was"``.

    The site styled the first letter of each blurb separately, which leaves a
    space after it once tags are removed.

    References:
        [PY-RE] https://docs.python.org/3/library/re.html
    """
    # "A" and "I" are real words ("A town in...", "I am"), so they are only joined to a
    # lone following letter: "A n " -> "An ", "A l Gore" -> "Al Gore", "I t " -> "It ".
    text = re.sub(r"^([B-HJ-Z]) (?=[A-Za-z])", r"\1", text)
    text = re.sub(r"^([AI]) ([a-z]) ", r"\1\2 ", text)
    # Mid-text drop caps follow sentence ends; skip "I" and "A", which are real words.
    return re.sub(r"(?<=[.!?] )([B-HJ-Z]) (?=[a-z])", r"\1", text)


class Linearizer(HTMLParser):
    """Flatten HTML into text with ``⟦HR⟧``, ``⟦B:…⟧`` and ``⟦A:slug|ext|text⟧`` markers.

    References:
        [PY-HTML-PARSER] HTMLParser callbacks, convert_charrefs,
            https://docs.python.org/3/library/html.parser.html
        [PY-URLLIB-PARSE] urljoin for relative links,
            https://docs.python.org/3/library/urllib.parse.html
    """

    def __init__(self, base_url: str) -> None:
        """Create a linearizer resolving links against ``base_url``. References: None."""
        super().__init__(convert_charrefs=True)
        self.base_url = base_url
        self.parts: list[str] = []
        self._bold = 0
        self._skip = 0
        self._skip_container: list[str] = []  # open tags inside a SKIP_IDS container
        self._anchor: tuple[str, str, list[str]] | None = None

    def _sanitize(self, data: str) -> str:
        """Remove marker characters from page text. References: None."""
        return data.replace("\u27e6", "[").replace("\u27e7", "]").replace("|", "/")

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        """Open bold runs and audio anchors; emit boundaries. References: [PY-HTML-PARSER]."""
        if self._skip_container or dict(attrs).get("id") in SKIP_IDS:
            if tag not in VOID_TAGS:
                self._skip_container.append(tag)
            return
        if tag in SKIP_TAGS:
            self._skip += 1
        elif tag == "hr":
            self._close_anchor()
            self.parts.append(f" {HR} ")
        elif tag == "a":
            self._close_anchor()
            href = dict(attrs).get("href") or ""
            af = audio_file(urljoin(self.base_url, href)) if href else None
            if af:
                if self._bold:
                    self.parts.append(CLOSE)
                self._anchor = (af.slug, af.ext, [])
        elif tag in BOLD_TAGS and self._anchor is None:
            if self._bold == 0:
                self.parts.append(f" {B_OPEN}")
            self._bold += 1
        elif tag in BREAK_TAGS:
            self.parts.append(" ")

    def handle_endtag(self, tag: str) -> None:
        """Close bold runs and audio anchors. References: [PY-HTML-PARSER]."""
        if self._skip_container:
            if tag in self._skip_container:  # tolerate unclosed inner tags
                del self._skip_container[len(self._skip_container) - 1 - self._skip_container[::-1].index(tag):]
            return
        if tag in SKIP_TAGS:
            self._skip = max(0, self._skip - 1)
        elif tag == "a":
            self._close_anchor()
        elif tag in BOLD_TAGS and self._anchor is None and self._bold:
            self._bold -= 1
            if self._bold == 0:
                self.parts.append(f"{CLOSE} ")
        elif tag in BREAK_TAGS:
            self.parts.append(" ")

    def handle_data(self, data: str) -> None:
        """Route text to the open anchor or the output. References: [PY-HTML-PARSER]."""
        if self._skip or self._skip_container:
            return
        data = self._sanitize(data)
        if self._anchor is not None:
            self._anchor[2].append(data)
        else:
            self.parts.append(data)

    def _close_anchor(self) -> None:
        """Emit the pending audio anchor marker, reopening bold if needed. References: None."""
        if self._anchor is None:
            return
        slug, ext, text = self._anchor
        self.parts.append(f" {A_OPEN}{slug}|{ext}|{' '.join(''.join(text).split())}{CLOSE} ")
        self._anchor = None
        if self._bold:
            self.parts.append(B_OPEN)

    def text(self) -> str:
        """Return the flattened stream with empty bold runs removed. References: None."""
        self._close_anchor()
        if self._bold:
            self.parts.append(CLOSE)
        out = " ".join("".join(self.parts).split())
        return re.sub("\u27e6B:\\s*\u27e7", " ", out)


def linearize(html: str, base_url: str) -> str:
    """Flatten an HTML page into the marker stream.

    References:
        [PY-HTML-PARSER] https://docs.python.org/3/library/html.parser.html
    """
    parser = Linearizer(base_url)
    try:
        parser.feed(html)
        parser.close()
    except Exception:  # malformed 1990s markup; keep what was parsed
        pass
    return parser.text()


@dataclass(frozen=True)
class Sighting:
    """One appearance of a song's audio link on an archived page.

    Attributes:
        slug: Audio file slug.
        title: Song title found on the page, or ``""``.
        title_from: ``"link"`` (link text) or ``"bold"`` (adjacent bold text) or ``""``.
        original_song: Bracketed name of the song being parodied, or ``""``.
        album: Album name from "From the album ...", or ``""``.
        album_year: Album year if given, or ``""``.
        week: "Week of ..." date text, or ``""``.
        description: Plain-text blurb preceding the song, or ``""``.

    References:
        [PY-DATACLASSES] https://docs.python.org/3/library/dataclasses.html
    """

    slug: str
    title: str = ""
    title_from: str = ""
    original_song: str = ""
    album: str = ""
    album_year: str = ""
    week: str = ""
    description: str = ""


def _groups(segment: str) -> list[tuple[str, int, int]]:
    """Group consecutive audio anchors for the same slug.

    Returns:
        ``(slug, start, end)`` per group, in page order.

    References:
        [PY-RE] re.finditer, https://docs.python.org/3/library/re.html
    """
    groups: list[tuple[str, int, int]] = []
    for m in ANCHOR_RE.finditer(segment):
        slug = m.group(1)
        if groups and groups[-1][0] == slug:
            groups[-1] = (slug, groups[-1][1], m.end())
        else:
            groups.append((slug, m.start(), m.end()))
    return groups


def _pick_title(segment: str, start: int, end: int, before_floor: int, after_ceiling: int) -> tuple[str, str, int]:
    """Choose a title for an anchor group.

    Order: non-generic link text; bold inside the group; first bold after the
    group; last bold before it. Bold runs that are all upper case (drop-cap
    openers such as "B YE, BYE BILL!") are ignored, as is text that does not
    look like a title (:func:`looks_like_title`) and link text that runs on into
    a sentence ("the Bush tax cut rates"). A trailing format note such as
    "(MP3)" is removed.

    Returns:
        ``(title, title_from, position_after_title)``; title ``""`` if none.

    References:
        [WAYBACK-CAPSTEPS-HOME] observed layouts, https://web.archive.org/web/2006*/capsteps.com/
    """
    for link in ANCHOR_RE.finditer(segment, start, end):
        text = FORMAT_SUFFIX_RE.sub("", clean(link.group(3)))
        prose = PROSE_AFTER_RE.match(segment, link.end()) or PROSE_BEFORE_RE.search(segment, 0, link.start())
        if not is_generic(text) and looks_like_title(text) and not prose:
            return text, "link", end

    def usable(m: re.Match) -> bool:
        text = clean(m.group(1))
        return len(text) > 2 and not is_generic(text) and text != text.upper() and looks_like_title(text)

    def title(m: re.Match) -> str:
        return FORMAT_SUFFIX_RE.sub("", clean(m.group(1)))

    inside = [m for m in BOLD_RE.finditer(segment, start, end) if usable(m)]
    if inside:
        return title(inside[0]), "bold", inside[0].end()
    after = [m for m in BOLD_RE.finditer(segment, end, min(after_ceiling, end + TITLE_WINDOW)) if usable(m)]
    if after:
        return title(after[0]), "bold", after[0].end()
    before = [m for m in BOLD_RE.finditer(segment, max(before_floor, start - TITLE_WINDOW), start) if usable(m)]
    if before:
        return title(before[-1]), "bold", before[-1].end()
    return "", "", end


def _original_song(segment: str, pos: int, ceiling: int) -> str:
    """Return the first non-generic bracketed text after ``pos`` (the parodied song).

    References:
        [PY-RE] https://docs.python.org/3/library/re.html
    """
    stripped = ANCHOR_RE.sub(lambda m: f" {A_OPEN}{CLOSE} ", segment[pos:ceiling])
    for m in BRACKET_RE.finditer(stripped):
        text = clean(m.group(1))
        if text and not is_generic(text) and not NOT_ORIGINAL_RE.search(text):
            return text
    return ""


def extract_sightings(html: str, base_url: str) -> list[Sighting]:
    """Extract every song sighting from one archived page.

    Args:
        html: Raw archived HTML.
        base_url: The capture's original URL (for resolving relative links).

    Returns:
        One :class:`Sighting` per audio-link group, in page order.

    References:
        [WAYBACK-CAPSTEPS-HOME] https://web.archive.org/web/2006*/capsteps.com/
        [PY-RE] https://docs.python.org/3/library/re.html
    """
    sightings: list[Sighting] = []
    for segment in linearize(html, base_url).split(HR):
        groups = _groups(segment)
        for index, (slug, start, end) in enumerate(groups):
            floor = groups[index - 1][2] if index else 0
            ceiling = groups[index + 1][1] if index + 1 < len(groups) else len(segment)
            title, title_from, title_end = _pick_title(segment, start, end, floor, ceiling)
            after = segment[end:ceiling]
            album_match = ALBUM_RE.search(clean_keep_markers(after))
            album, album_year = clean_album(album_match.group(1), album_match.group(2) or "") if album_match else ("", "")
            before_text = segment[floor:start]
            week_match = WEEK_RE.search(before_text) or WEEK_RE.search(segment[:start])
            description = before_text
            if title and title_from == "bold" and title_end <= start:
                description = segment[floor:segment.rfind(B_OPEN, floor, start)]
            # 1996-2010 blurbs open with an all-caps bold lead ("FOLLOWING THE TRAGIC ...", or a
            # drop cap "J"); start there, dropping unrelated notes earlier in the same block (20021030004940).
            leads = [m.start() for m in BOLD_RE.finditer(description) if _is_lead(m.group(1))]
            if leads:
                description = description[leads[-1]:]
            description = _blurb(description)
            # An earlier song linked inline in the same paragraph ("such as the Wedtech scandal,
            # the Iran-Contra scandal, ...") cuts the blurb mid-sentence; extend it back over that
            # link, keeping the link text.
            back = index
            while description[:1].islower() and back > 0:
                back -= 1
                back_floor = groups[back - 1][2] if back else 0
                description = _blurb(ANCHOR_RE.sub(lambda m: f" {m.group(3)} ", segment[back_floor:start]))
            sightings.append(Sighting(
                slug=slug,
                title=title,
                title_from=title_from,
                original_song=_original_song(segment, title_end if title else start, ceiling),
                album=album,
                album_year=album_year,
                week=week_match.group(1) if week_match else "",
                description=description,
            ))
    return sightings


def _is_lead(text: str) -> bool:
    """True for an all-caps bold blurb opener such as ``"IT'S TAX TIME"`` or a drop cap ``"J"``.

    References:
        None.
    """
    text = text.strip()
    return bool(re.search(r"[A-Z]", text)) and text == text.upper()


def _blurb(text: str) -> str:
    """Turn a stretch of the marker stream into description text.

    References:
        [PY-RE] https://docs.python.org/3/library/re.html
    """
    text = WEEK_RE.sub(" ", text)
    return fix_drop_cap(clean(JUNK_RE.sub(" ", BRACKET_RE.sub(" ", text))))


def clean_album(text: str, year: str = "") -> tuple[str, str]:
    """Tidy an album name and pull out a "(Songs of 2010)" year.

    Removes debris left by the surrounding sentence, e.g. ``"! Desperate Housemembers"``
    and ``"76 Bad Loans.)"`` (from "(From the album 76 Bad Loans.)").

    Returns:
        ``(album, year)``; ``year`` is the given year unless the name supplied one.

    References:
        [PY-RE] https://docs.python.org/3/library/re.html
    """
    text = clean(text).lstrip("!.,;: ")
    songs_of = re.search(r"\s*\(Songs of (\d{4})\)\s*$", text, re.I)
    if songs_of:
        text, year = text[:songs_of.start()], year or songs_of.group(1)
    while text.endswith((")", ".", " ")) and (not text.endswith(")") or text.count(")") > text.count("(")):
        text = text[:-1]
    return text, year


def clean_keep_markers(text: str) -> str:
    """Replace anchor markers with their link text so album names in links survive.

    References:
        [PY-RE] https://docs.python.org/3/library/re.html
    """
    text = ANCHOR_RE.sub(lambda m: f" {m.group(3)} ", text)
    text = BOLD_RE.sub(lambda m: f" {m.group(1)} ", text)
    return " ".join(text.split())


def extract_copyright(html: str) -> str:
    """Return the page's copyright, parody, and usage notices, as written, or ``""``.

    References:
        [PY-HTML] html.unescape, https://docs.python.org/3/library/html.html
        [PY-RE] https://docs.python.org/3/library/re.html
    """
    text = unescape(clean(linearize(html, "http://www.capsteps.com/")))  # some pages double-escape &copy;
    found = sorted((m.start(), m.group(0)) for rx in NOTICE_RES if (m := rx.search(text)))
    # Close the "(Recordings ... prior to" parenthetical, which the site often left open.
    parts = [part + ")" if part.startswith("(") and not part.endswith(")") else part for _, part in found]
    return " ".join(" ".join(parts).split())
