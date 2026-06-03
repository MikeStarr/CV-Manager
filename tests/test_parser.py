"""Tests for the :mod:`cv_manager.parser.cv_parser` module.

The real parser requires a ``.docx`` file to read from.  The test suite
skips the actual parsing step if the expected sample file is not present in
the repository – this keeps the tests lightweight and avoids hard‑coding a
large document into the repo.
"""

import os
from pathlib import Path

import pytest

# Import the class under test.  The module is part of the package, so it can be
# imported directly after the editable install has been performed.
from cv_manager.parser.cv_parser import CVParser


@pytest.mark.skipif(
    not Path("cvs/test_cv.docx").exists(),
    reason="Sample .docx file missing – skipping parser test.",
)
def test_cvparser_parse() -> None:
    """Verify that :class:`CVParser` can be instantiated and returns a list."""

    parser = CVParser("cvs/test_cv.docx")
    elements = parser.parse()
    assert isinstance(elements, list)