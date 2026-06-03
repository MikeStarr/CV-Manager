"""Core Streamlit UI logic for CV‑Manager.

The UI allows the user to paste a job specification or upload a text file. The
specification is parsed into a simple dictionary of keywords. All CVs in
``src/cv_manager/data/`` are loaded, scored against the spec using a very
simple TF‑IDF style match (for demonstration purposes).  The best matching
CV is displayed with its score.

The module keeps dependencies minimal – only ``streamlit`` and standard
library modules.  Word file handling is delegated to :mod:`cv_manager.parser`.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Dict, Iterable, List, Tuple

import streamlit as st

# Local imports – these are lightweight and safe to import at runtime.
from .parser.cv_parser import load_cv_text  # type: ignore
from .utils import score_cv_against_spec  # type: ignore

DATA_DIR = Path(__file__).parent.parent / "data"
CV_FILES = list(DATA_DIR.glob("*.docx"))

# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------

def _load_all_cvs() -> List[Tuple[str, str]]:
    """Return a list of (filename, text) tuples for all CVs.

    The function reads each Word file using :func:`cv_manager.parser.cv_parser.load_cv_text`.
    It returns the raw text; formatting is preserved in the original file but not
    needed for scoring.
    """
    cvs: List[Tuple[str, str]] = []
    for fp in CV_FILES:
        try:
            txt = load_cv_text(fp)
            cvs.append((fp.name, txt))
        except Exception as exc:  # pragma: no cover - defensive
            st.warning(f"Could not read {fp.name}: {exc}")
    return cvs

# ---------------------------------------------------------------------------
# Streamlit UI
# ---------------------------------------------------------------------------

def run_app() -> None:
    """Main entry point for the Streamlit app.

    The function is intentionally small – it only sets up the layout and
    delegates heavy work to helper functions.  This keeps the global module
    import lightweight.
    """
    st.set_page_config(page_title="CV‑Manager", page_icon="📄")
    st.title("CV‑Manager – Find the best CV for a job spec")

    # Job specification input
    with st.expander("Enter job specification", expanded=True):
        spec_text = st.text_area(
            "Paste job description here (plain text or upload .txt)", height=200
        )
        uploaded = st.file_uploader("Or upload a .txt file", type=["txt"])
        if uploaded:
            try:
                spec_text = uploaded.getvalue().decode("utf-8")
            except Exception as exc:  # pragma: no cover - defensive
                st.error(f"Failed to read uploaded file: {exc}")

    if not spec_text.strip():
        st.info("Please provide a job specification.")
        return

    # Parse spec into keyword dict – simple split on whitespace for demo.
    spec_keywords = {
        word.lower() for word in spec_text.split() if len(word) > 2
    }

    st.subheader("Searching CVs…")
    cvs = _load_all_cvs()
    if not cvs:
        st.error("No CV files found.")
        return

    # Score each CV and find the best match.
    scored: List[Tuple[str, float]] = []
    for name, text in cvs:
        score = score_cv_against_spec(text, spec_keywords)
        scored.append((name, score))

    scored.sort(key=lambda x: x[1], reverse=True)
    best_name, best_score = scored[0]

    st.success(f"Best match: **{best_name}** (score {best_score:.2f})")
    st.markdown("---")
    st.subheader("Top 5 CVs")
    for name, score in scored[:5]:
        st.write(f"• *{name}* – {score:.2f}")

    # Optionally display the best CV text.
    with st.expander("Show best CV content", expanded=False):
        _, best_text = next((n, t) for n, t in cvs if n == best_name)
        st.text_area("Best CV", best_text, height=300)

# End of file
