"""Tests for tools/lint_citations.py.

References:
    [PYTEST-DOCS] https://docs.pytest.org/en/stable/
"""

from pathlib import Path
from textwrap import dedent

import pytest

from lint_citations import lint_source, main, references_section

KNOWN = {"IA-CDX-API", "PY-RE"}
# Built from parts so build_bibliography.py does not see a citation of an unregistered ID.
UNKNOWN = "[NOT" + "-REAL]"


def lint(source: str) -> list[str]:
    """Lint a snippet and return ``name: message`` strings. References: None."""
    return [f"{p.name}: {p.message}" for p in lint_source(dedent(source), Path("x.py"), KNOWN)]


MODULE = '"""Module. References: None."""\n'


@pytest.mark.parametrize(
    "docstring",
    [
        "One line. References: None.",
        "One line. References: [PY-RE].",
        "Summary.\n\n    Args:\n        x: y.\n\n    References:\n        [IA-CDX-API] https://example.org\n    ",
        "Summary.\n\n    References:\n        None (project rule).\n    ",
    ],
)
def test_accepts_cited_or_none(docstring):
    """Inline and section forms pass with a known ID or None. References: [GOOGLE-PYGUIDE]."""
    assert lint(MODULE + f'def f():\n    """{docstring}"""\n') == []


@pytest.mark.parametrize(
    ("body", "message"),
    [
        ("pass", "missing docstring with a References: section"),
        ('"""No section."""', "docstring has no References: section"),
        ('"""Empty.\n\n    References:\n    """', "References: section must cite an [ID] or say None"),
        (f'"""Unknown. References: {UNKNOWN}."""', f"cites {UNKNOWN}, which is not in references/references.yaml"),
        ('"""Mentions ``References:`` [PY-RE] only in prose."""', "docstring has no References: section"),
    ],
)
def test_rejects(body, message):
    """Missing, empty, unknown and prose-only sections fail. References: None."""
    assert lint(MODULE + f"def f():\n    {body}\n") == [f"f: {message}"]


def test_checks_module_classes_methods_and_nested_functions():
    """Every unit is checked and named by its enclosing scopes. References: [PY-AST]."""
    source = """
    class C:
        def m(self):
            def inner():
                pass
    """
    assert lint(source) == [
        "<module>: missing docstring with a References: section",
        "C: missing docstring with a References: section",
        "C.m: missing docstring with a References: section",
        "C.m.inner: missing docstring with a References: section",
    ]


def test_section_ends_at_next_header():
    """IDs under a later section are not counted as references. References: None."""
    doc = "Summary.\n\nReferences:\n\nNotes:\n    [PY-RE] elsewhere.\n"
    assert references_section(doc).strip() == ""
    assert lint(MODULE + f'def f():\n    """{doc}"""\n') == ["f: References: section must cite an [ID] or say None"]


def test_repository_is_clean(capsys):
    """The real ingest/ and tools/ code passes the lint. References: None."""
    assert main([]) == 0, capsys.readouterr().err
