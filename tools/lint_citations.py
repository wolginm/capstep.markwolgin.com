#!/usr/bin/env python3
"""Fail if any Python module, class, function or method lacks a citation section.

CLAUDE.md requires every method to list the sources it uses. In Python that list
is a Google-style ``References:`` section in the docstring [GOOGLE-PYGUIDE]. It
must cite at least one registered ID (``[IA-CDX-API]``) or say ``None``, and every
ID it cites must exist in ``references/references.yaml``. One-line docstrings may
end with an inline ``References: None.`` or ``References: [ID].``

Nested functions count too. TypeScript is checked by ``web/scripts/lint-citations.ts``.

Usage:
    python3 tools/lint_citations.py            # lint ingest/ and tools/
    python3 tools/lint_citations.py PATH ...   # lint specific files or directories

References:
    [PY-AST] ast.parse, ast.walk, ast.get_docstring, https://docs.python.org/3/library/ast.html
    [GOOGLE-PYGUIDE] docstring sections, https://google.github.io/styleguide/pyguide.html
    [PY-RE] https://docs.python.org/3/library/re.html
    [PY-ARGPARSE] https://docs.python.org/3/library/argparse.html
    [PY-PATHLIB] https://docs.python.org/3/library/pathlib.html
"""

from __future__ import annotations

import argparse
import ast
import re
import sys
from dataclasses import dataclass
from pathlib import Path

from build_bibliography import CITATION_PATTERN, REFERENCES_FILE, REPO_ROOT, SKIP_DIRS, load_references

DEFAULT_ROOTS = (REPO_ROOT / "ingest", REPO_ROOT / "tools")
# "References:" at a line start or after a space; ``References:`` in prose does not count.
REFERENCES_RE = re.compile(r"(?:^|(?<=\s))References:(.*)", re.DOTALL | re.MULTILINE)
# Any other Google-style section header ends the References section.
NEXT_SECTION_RE = re.compile(r"^\s*[A-Z][A-Za-z ]*:\s*$", re.MULTILINE)
NONE_RE = re.compile(r"^\s*None\b")

Unit = ast.Module | ast.ClassDef | ast.FunctionDef | ast.AsyncFunctionDef


@dataclass(frozen=True)
class Problem:
    """One lint failure, printed as ``path:line: name: message``.

    References:
        [PY-DATACLASSES] https://docs.python.org/3/library/dataclasses.html
    """

    path: Path
    line: int
    name: str
    message: str

    def __str__(self) -> str:
        """Format like a compiler diagnostic. References: None."""
        try:
            shown = self.path.relative_to(REPO_ROOT).as_posix()
        except ValueError:
            shown = str(self.path)
        return f"{shown}:{self.line}: {self.name}: {self.message}"


def references_section(docstring: str) -> str | None:
    """Return the text of a docstring's References section, or None if it has none.

    Args:
        docstring: A cleaned docstring (``ast.get_docstring``).

    Returns:
        The text after ``References:`` up to the next section header or the end.

    References:
        [GOOGLE-PYGUIDE] section headers end with a colon,
            https://google.github.io/styleguide/pyguide.html
        [PY-RE] re.Pattern.search, https://docs.python.org/3/library/re.html
    """
    match = REFERENCES_RE.search(docstring)
    if not match:
        return None
    body = match.group(1)
    following = NEXT_SECTION_RE.search(body)
    return body[: following.start()] if following else body


def check_docstring(docstring: str | None, known: set[str]) -> list[str]:
    """List what is wrong with one docstring's citations (empty if nothing).

    Args:
        docstring: The unit's docstring, or None if it has none.
        known: Every ID in the reference registry.

    Returns:
        Human-readable problems.

    References:
        None (project rule, CLAUDE.md and plan/PLAN.md §7).
    """
    if not docstring:
        return ["missing docstring with a References: section"]
    section = references_section(docstring)
    if section is None:
        return ["docstring has no References: section"]
    cited = CITATION_PATTERN.findall(section)
    if not cited and not NONE_RE.match(section):
        return ["References: section must cite an [ID] or say None"]
    return [f"cites [{ref_id}], which is not in references/references.yaml" for ref_id in cited if ref_id not in known]


def unit_name(node: Unit, parents: dict[ast.AST, ast.AST]) -> str:
    """Dotted name such as ``CdxClient.fetch`` or ``<module>``.

    Args:
        node: The module, class or function.
        parents: Child-to-parent map for the module's tree.

    Returns:
        The name, qualified by enclosing classes and functions.

    References:
        [PY-AST] node classes, https://docs.python.org/3/library/ast.html
    """
    if isinstance(node, ast.Module):
        return "<module>"
    names = [node.name]
    parent = parents.get(node)
    while parent is not None and not isinstance(parent, ast.Module):
        if isinstance(parent, ast.ClassDef | ast.FunctionDef | ast.AsyncFunctionDef):
            names.append(parent.name)
        parent = parents.get(parent)
    return ".".join(reversed(names))


def lint_source(source: str, path: Path, known: set[str]) -> list[Problem]:
    """Check every module, class and function in one Python source file.

    Args:
        source: The file's text.
        path: Where it came from (used only in messages).
        known: Every ID in the reference registry.

    Returns:
        Problems in source order.

    References:
        [PY-AST] ast.parse, ast.walk, ast.iter_child_nodes, ast.get_docstring,
            https://docs.python.org/3/library/ast.html
    """
    tree = ast.parse(source, filename=str(path))
    parents = {child: node for node in ast.walk(tree) for child in ast.iter_child_nodes(node)}
    problems = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Module | ast.ClassDef | ast.FunctionDef | ast.AsyncFunctionDef):
            for message in check_docstring(ast.get_docstring(node), known):
                problems.append(Problem(path, getattr(node, "lineno", 1), unit_name(node, parents), message))
    return sorted(problems, key=lambda p: p.line)


def python_files(paths: list[Path]) -> list[Path]:
    """Expand files and directories into the sorted list of .py files to lint.

    Args:
        paths: Files or directories.

    Returns:
        Python files, skipping caches, virtual environments and dependencies.

    References:
        [PY-PATHLIB] Path.rglob, https://docs.python.org/3/library/pathlib.html
    """
    found: set[Path] = set()
    for path in paths:
        if path.is_file():
            found.add(path.resolve())
            continue
        for file in path.rglob("*.py"):
            if not SKIP_DIRS.intersection(file.relative_to(path).parts):
                found.add(file.resolve())
    return sorted(found)


def main(argv: list[str] | None = None) -> int:
    """Command-line entry point.

    Args:
        argv: Argument list (defaults to ``sys.argv[1:]``).

    Returns:
        0 if every unit is cited, 1 otherwise.

    References:
        [PY-ARGPARSE] positional nargs="*", https://docs.python.org/3/library/argparse.html
    """
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("paths", nargs="*", type=Path, help="files or directories (default: ingest/ and tools/)")
    args = parser.parse_args(argv)

    known = {entry["id"] for entry in load_references(REFERENCES_FILE)}
    files = python_files(args.paths or list(DEFAULT_ROOTS))
    problems = [p for file in files for p in lint_source(file.read_text(encoding="utf-8"), file, known)]
    for problem in problems:
        print(problem, file=sys.stderr)
    print(f"lint_citations: {len(files)} Python files, {len(problems)} problems")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
