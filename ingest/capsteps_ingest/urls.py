"""URL normalization helpers for archived capsteps.com URLs.

The Wayback Machine records the same file under several spellings
(``http``/``https``, with or without ``www.``, with an explicit ``:80``). These
helpers collapse those spellings so captures can be grouped per file and per song.

References:
    [RFC-3986] RFC 3986 §6.2.2–6.2.3 (case and port normalization),
        https://datatracker.ietf.org/doc/html/rfc3986
    [PY-URLLIB-PARSE] Python docs, urllib.parse,
        https://docs.python.org/3/library/urllib.parse.html
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import PurePosixPath
from urllib.parse import unquote, urlsplit

DEFAULT_PORTS = {"http": "80", "https": "443"}

PLAYABLE_EXTS = frozenset({"mp3"})
LEGACY_EXTS = frozenset({"au", "ra", "ram", "rm", "wav", "aif", "aiff", "snd"})
AUDIO_EXTS = PLAYABLE_EXTS | LEGACY_EXTS


@dataclass(frozen=True)
class AudioFile:
    """An audio file identified from an archived URL.

    Attributes:
        canonical: Normalized URL without scheme, e.g. ``capsteps.com/sounds/401k.mp3``.
        directory: Directory path, e.g. ``/sounds/``.
        slug: Lower-cased file name without extension, e.g. ``401k-obamamia``.
        ext: Lower-cased extension without the dot, e.g. ``mp3``.

    References:
        [PY-DATACLASSES] Python docs, dataclasses (frozen=True),
            https://docs.python.org/3/library/dataclasses.html
    """

    canonical: str
    directory: str
    slug: str
    ext: str


def canonical_url(original: str) -> str:
    """Normalize an archived URL so spelling variants compare equal.

    Drops the scheme, lower-cases the host, strips a leading ``www.`` and any
    default port, and drops the fragment. The path and query are kept as-is
    (paths are case-sensitive per RFC 3986).

    Args:
        original: URL as recorded in the CDX ``original`` field.

    Returns:
        Normalized ``host/path[?query]`` string.

    References:
        [RFC-3986] §6.2.2.1 (case normalization), §6.2.3 (scheme-based / port
            normalization), https://datatracker.ietf.org/doc/html/rfc3986
        [PY-URLLIB-PARSE] urlsplit, https://docs.python.org/3/library/urllib.parse.html
    """
    parts = urlsplit(original.strip())
    host = (parts.hostname or "").lower()
    if host.startswith("www."):
        host = host[4:]
    port = parts.port
    if port is not None and str(port) != DEFAULT_PORTS.get(parts.scheme.lower(), ""):
        host = f"{host}:{port}"
    path = parts.path or "/"
    query = f"?{parts.query}" if parts.query else ""
    return f"{host}{path}{query}"


def audio_file(original: str) -> AudioFile | None:
    """Identify an audio file from an archived URL by its extension.

    Args:
        original: URL as recorded in the CDX ``original`` field.

    Returns:
        An :class:`AudioFile`, or ``None`` if the URL's extension is not a known
        audio extension.

    References:
        [PY-PATHLIB] PurePosixPath.stem / suffix / parent,
            https://docs.python.org/3/library/pathlib.html
        [PY-URLLIB-PARSE] urlsplit, unquote,
            https://docs.python.org/3/library/urllib.parse.html
    """
    path = PurePosixPath(unquote(urlsplit(original.strip()).path))
    ext = path.suffix.lower().lstrip(".")
    if ext not in AUDIO_EXTS or not path.stem:
        return None
    directory = str(path.parent)
    directory = directory if directory.endswith("/") else f"{directory}/"
    return AudioFile(
        canonical=canonical_url(original),
        directory=directory,
        slug=path.stem.lower(),
        ext=ext,
    )


def wayback_raw_url(timestamp: str, original: str) -> str:
    """Build the Wayback URL that serves a capture's original bytes.

    Args:
        timestamp: 14-digit CDX timestamp.
        original: URL as recorded in the CDX ``original`` field.

    Returns:
        ``https://web.archive.org/web/<timestamp>id_/<original>``.

    References:
        [IA-WAYBACK-URL] Source for the ``id_`` flag still to be identified
            (see plan §7); the form is observed Wayback behaviour.
    """
    return f"https://web.archive.org/web/{timestamp}id_/{original}"


def wayback_view_url(timestamp: str, original: str) -> str:
    """Build the normal (toolbar) Wayback Machine URL for a capture.

    Args:
        timestamp: 14-digit CDX timestamp.
        original: URL as recorded in the CDX ``original`` field.

    Returns:
        ``https://web.archive.org/web/<timestamp>/<original>``.

    References:
        [WAYBACK-CAPSTEPS-SONGS] Wayback Machine URL form as used in CLAUDE.md,
            https://web.archive.org/web/20260000000000*/https://www.capsteps.com/songs/
    """
    return f"https://web.archive.org/web/{timestamp}/{original}"
