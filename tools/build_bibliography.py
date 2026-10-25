#!/usr/bin/env python3
"""Generate BIBLIOGRAPHY.md from references/references.yaml.

Validates the reference registry, scans the repository for bracketed citations
such as ``[IA-CDX-API]``, and writes a Markdown bibliography that lists every
reference together with the files that cite it.

Usage:
    python3 tools/build_bibliography.py          # write BIBLIOGRAPHY.md
    python3 tools/build_bibliography.py --check  # exit 1 if BIBLIOGRAPHY.md is stale

References:
    [PYYAML-DOCS] PyYAML Documentation, https://pyyaml.org/wiki/PyYAMLDocumentation
    [PY-ARGPARSE] Python docs, argparse, https://docs.python.org/3/library/argparse.html
    [PY-RE] Python docs, re, https://docs.python.org/3/library/re.html
    [PY-PATHLIB] Python docs, pathlib, https://docs.python.org/3/library/pathlib.html
    [PY-OS-WALK] Python docs, os.walk, https://docs.python.org/3/library/os.html#os.walk
    [GOOGLE-PYGUIDE] Google Python Style Guide, https://google.github.io/styleguide/pyguide.html
"""

from __future__ import annotations

import argparse
import os
import re
import sys
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
REFERENCES_FILE = REPO_ROOT / "references" / "references.yaml"
BIBLIOGRAPHY_FILE = REPO_ROOT / "BIBLIOGRAPHY.md"

REQUIRED_FIELDS = ("id", "title", "url", "accessed")
# IDs need a letter-led first segment of 2+ chars and at least one hyphen, so that
# regex classes like "[A-Z0-9]" or Markdown such as "[OK]" are not taken as citations.
ID_PATTERN = re.compile(r"^[A-Z][A-Z0-9]+(?:-[A-Z0-9]+)+$")
CITATION_PATTERN = re.compile(r"\[([A-Z][A-Z0-9]+(?:-[A-Z0-9]+)+)\]")

SKIP_DIRS = {".git", "node_modules", "dist", ".venv", "__pycache__", "cache"}
SCAN_SUFFIXES = {".py", ".ts", ".tsx", ".js", ".md", ".yaml", ".yml", ".html", ".css"}
SCAN_NAMES = {".gitignore"}
SKIP_FILES = {BIBLIOGRAPHY_FILE, REFERENCES_FILE}


def load_references(path: Path) -> list[dict]:
    """Load and validate the reference registry.

    Args:
        path: Path to references.yaml.

    Returns:
        The list of reference entries, in file order.

    Raises:
        ValueError: If an entry is missing a required field, has a malformed ID,
            or duplicates another entry's ID.

    References:
        [PYYAML-DOCS] yaml.safe_load, https://pyyaml.org/wiki/PyYAMLDocumentation
        [PY-RE] re.Pattern.match, https://docs.python.org/3/library/re.html
    """
    with path.open(encoding="utf-8") as handle:
        data = yaml.safe_load(handle) or {}

    entries = data.get("references") or []
    seen: set[str] = set()
    for index, entry in enumerate(entries):
        missing = [field for field in REQUIRED_FIELDS if not entry.get(field)]
        if missing:
            raise ValueError(f"reference #{index + 1} is missing {', '.join(missing)}")
        ref_id = entry["id"]
        if not ID_PATTERN.match(ref_id):
            raise ValueError(f"reference ID {ref_id!r} is not UPPER-KEBAB-CASE with at least two segments")
        if ref_id in seen:
            raise ValueError(f"duplicate reference ID {ref_id!r}")
        seen.add(ref_id)
    return entries


def find_citations(root: Path) -> dict[str, set[str]]:
    """Map each bracketed citation ID found in the repo to the files citing it.

    Args:
        root: Repository root to scan.

    Returns:
        Mapping of citation ID to a set of repo-relative POSIX paths.

    References:
        [PY-OS-WALK] os.walk with in-place pruning of dirnames,
            https://docs.python.org/3/library/os.html#os.walk
        [PY-RE] re.Pattern.findall, https://docs.python.org/3/library/re.html
        [PY-PATHLIB] PurePath.relative_to / as_posix,
            https://docs.python.org/3/library/pathlib.html
    """
    citations: dict[str, set[str]] = {}
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = sorted(d for d in dirnames if d not in SKIP_DIRS)
        for filename in sorted(filenames):
            path = Path(dirpath) / filename
            if (path.suffix not in SCAN_SUFFIXES and path.name not in SCAN_NAMES) or path in SKIP_FILES:
                continue
            text = path.read_text(encoding="utf-8", errors="ignore")
            for ref_id in CITATION_PATTERN.findall(text):
                citations.setdefault(ref_id, set()).add(path.relative_to(root).as_posix())
    return citations


def format_entry(entry: dict) -> str:
    """Format one reference as a Markdown citation line.

    Args:
        entry: A validated reference entry.

    Returns:
        A citation of the form ``Author. *Title*. Publisher. <URL> (accessed DATE).``

    References:
        None (project convention, see plan/PLAN.md §7).
    """
    parts = []
    if entry.get("author"):
        parts.append(f"{entry['author']}.")
    parts.append(f"*{entry['title']}*.")
    if entry.get("publisher"):
        parts.append(f"{entry['publisher']}.")
    parts.append(f"<{entry['url']}> (accessed {entry['accessed']}).")
    return " ".join(parts)


def render_bibliography(entries: list[dict], citations: dict[str, set[str]]) -> str:
    """Render the full BIBLIOGRAPHY.md document.

    Args:
        entries: Validated reference entries.
        citations: Output of :func:`find_citations`.

    Returns:
        Markdown text for BIBLIOGRAPHY.md.

    References:
        None (project convention, see plan/PLAN.md §7).
    """
    lines = [
        "# Bibliography",
        "",
        "<!-- Generated by tools/build_bibliography.py from references/references.yaml."
        " Do not edit by hand. -->",
        "",
        "Every source consulted, quoted, or borrowed from in this project. Cite an entry"
        " in code or docs by writing its ID in square brackets.",
        "",
    ]
    for entry in sorted(entries, key=lambda e: e["id"]):
        lines.append(f"### [{entry['id']}]")
        lines.append("")
        lines.append(format_entry(entry))
        lines.append("")
        if entry.get("note"):
            lines.append(f"- **Used for:** {entry['note']}")
        cited_in = sorted(citations.get(entry["id"], ()))
        lines.append(f"- **Cited in:** {', '.join(f'`{p}`' for p in cited_in) or '_not yet cited_'}")
        lines.append("")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    """Command-line entry point.

    Args:
        argv: Argument list (defaults to ``sys.argv[1:]``).

    Returns:
        Process exit code: 0 on success, 1 if ``--check`` finds a stale file or
        unknown citation IDs are present.

    References:
        [PY-ARGPARSE] ArgumentParser, store_true actions,
            https://docs.python.org/3/library/argparse.html
    """
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--check",
        action="store_true",
        help="do not write; exit 1 if BIBLIOGRAPHY.md is out of date",
    )
    args = parser.parse_args(argv)

    entries = load_references(REFERENCES_FILE)
    citations = find_citations(REPO_ROOT)

    known = {entry["id"] for entry in entries}
    unknown = {ref_id: files for ref_id, files in citations.items() if ref_id not in known}
    for ref_id, files in sorted(unknown.items()):
        print(f"warning: [{ref_id}] cited in {', '.join(sorted(files))} but not in references.yaml",
              file=sys.stderr)

    rendered = render_bibliography(entries, citations)
    if args.check:
        current = BIBLIOGRAPHY_FILE.read_text(encoding="utf-8") if BIBLIOGRAPHY_FILE.exists() else ""
        if current != rendered:
            print("BIBLIOGRAPHY.md is out of date; run tools/build_bibliography.py", file=sys.stderr)
            return 1
        return 0

    BIBLIOGRAPHY_FILE.write_text(rendered, encoding="utf-8")
    print(f"wrote {BIBLIOGRAPHY_FILE.relative_to(REPO_ROOT)} ({len(entries)} references)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
