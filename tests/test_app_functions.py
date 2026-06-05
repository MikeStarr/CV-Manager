from __future__ import annotations

# Ensure the project root is on ``sys.path`` so that ``cv_manager`` can be imported.
import os
import sys

root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if root not in sys.path:
    sys.path.insert(0, root)

from src.cv_manager.app import get_docx_text, get_cv_files

"""Unit tests for helper functions in :mod:`src.cv_manager.app`.

Only the pure‑Python helpers are exercised – ``get_docx_text`` and
``get_cv_files``.  The UI logic inside :func:`main` is not testable without a
Streamlit environment, so it is intentionally omitted from this suite.
"""

import sys
import types
from pathlib import Path
from unittest.mock import MagicMock

import pytest

# ``docx`` is an optional dependency.  Importing the real library would pull in a
# large binary package which is unnecessary for unit tests, so we provide a very
# small stub that satisfies the attribute access performed by ``app.get_docx_text``.
sys.modules.setdefault("docx", types.SimpleNamespace(Document=lambda *a, **k: None))

# Import the module under test.  The package is added to ``sys.path`` by the
# application itself, but importing it directly keeps the intent clear.
import src.cv_manager.app as app


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
"""Unit tests for helper functions in :mod:`src.cv_manager.app`.

Only the pure‑Python helpers are exercised – ``get_docx_text`` and
``get_cv_files``.  The UI logic inside :func:`main` is not testable without a
Streamlit environment, so it is intentionally omitted from this suite.
"""


def test_get_docx_text(monkeypatch):
    """Verify that ``get_docx_text`` preserves bold and italic markers.

    The function relies on :class:`docx.Document`.  We monkey‑patch the class to
    return a controlled structure of paragraphs and runs.
    """

    # Create a fake document with two paragraphs.
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
    # Expected: *Hello* _World_\nFoo
    assert result == "*Hello*_World_\nFoo"


def test_get_cv_files(tmp_path, monkeypatch):
    """Ensure that only ``.docx`` files are returned and temporary files are ignored."""

    # Create a temporary directory mimicking the CV_DIR.
    cv_dir = tmp_path / "cvs"
    cv_dir.mkdir()
    # Create some test files
    (cv_dir / "template1.docx").write_text("dummy")
    (cv_dir / "~temp.docx").write_text("tmp")
    (cv_dir / "readme.md").write_text("ignore")

    # Monkeypatch the global CV_DIR to point at our temp dir.
    monkeypatch.setattr(app, "CV_DIR", str(cv_dir))
    files = app.get_cv_files()
    assert sorted(files) == ["template1.docx"]


def test_get_ats_keywords(mocker):
    """Verify that get_ats_keywords initializes CVBrain and extracts keywords correctly."""

    # Clear streamlit cache to prevent flakiness between test runs
    if hasattr(app.get_ats_keywords, "clear"):
        app.get_ats_keywords.clear()

    mock_brain_class = mocker.patch("src.cv_manager.app.CVBrain")
    mock_brain_instance = mocker.MagicMock()
    mock_brain_class.return_value = mock_brain_instance

    expected_result = {"technical_skills": ["Python"]}
    mock_brain_instance.extract_ats_keywords.return_value = expected_result

    result = app.get_ats_keywords(
        job_spec="Job spec text",
        base_url="http://test",
        api_key="test-key",
        model="test-model",
        timeout=10.0,
        provider="Local"
    )

    mock_brain_class.assert_called_once_with(
        api_key="test-key",
        base_url="http://test",
        model="test-model",
        timeout=10.0,
        provider="Local"
    )
    mock_brain_instance.extract_ats_keywords.assert_called_once_with("Job spec text")
    assert result == expected_result


# The ``load_registry`` helper is defined inside :func:`main` and therefore not
# importable from the module namespace.  Testing it directly would require
# executing the entire UI flow, which is outside the scope of a unit test.
