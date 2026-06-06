"""Unit tests for helper functions in :mod:`src.cv_manager.app`.

Only the pure‑Python helpers are exercised – ``get_docx_text`` and
``get_cv_files``.  The UI logic inside :func:`main` is not testable without a
Streamlit environment, so it is intentionally omitted from this suite.
"""

from __future__ import annotations

import os
import sys
from unittest.mock import MagicMock

# Ensure the project root is on ``sys.path`` so that ``cv_manager`` can be imported.
root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if root not in sys.path:
    sys.path.insert(0, root)

import src.cv_manager.app as app  # noqa: E402


def test_get_docx_text(monkeypatch):
    """Verify that bold and italic markers are preserved.

    ``app.get_docx_text`` iterates over :class:`docx.Document` paragraphs and
    runs.  We monkey‑patch the ``Document`` constructor to return a controlled
    object with two paragraphs containing styled runs.
    """

    paragraph1 = MagicMock()
    run_a = MagicMock(text="Hello", bold=True, italic=False)
    run_b = MagicMock(text="World", bold=False, italic=True)
    paragraph1.runs = [run_a, run_b]

    paragraph2 = MagicMock()
    run_c = MagicMock(text="Foo", bold=False, italic=False)
    paragraph2.runs = [run_c]

    fake_doc = MagicMock(paragraphs=[paragraph1, paragraph2])
    monkeypatch.setattr(app, "Document", lambda _: fake_doc)

    result = app.get_docx_text("dummy.docx")
    assert result == "*Hello*_World_\nFoo"


def test_get_cv_files(tmp_path, monkeypatch):
    """Ensure that only ``.docx`` files are returned and temporary files are ignored."""

    cv_dir = tmp_path / "cvs"
    cv_dir.mkdir()
    (cv_dir / "template1.docx").write_text("dummy")
    (cv_dir / "~temp.docx").write_text("tmp")
    (cv_dir / "readme.md").write_text("ignore")

    monkeypatch.setattr(app, "CV_DIR", str(cv_dir))
    files = app.get_cv_files()
    assert sorted(files) == ["template1.docx"]

# The ``load_registry`` helper is defined inside :func:`main` and therefore not
# importable from the module namespace.  Testing it directly would require
# executing the entire UI flow, which is outside the scope of a unit test.
