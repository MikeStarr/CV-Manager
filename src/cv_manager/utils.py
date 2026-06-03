def do_something_useful() -> None:
    print("Replace this with a utility function")

# ---------------------------------------------------------------------------
# Simple scoring helper
# ---------------------------------------------------------------------------
def score_cv_against_spec(cv_text: str, spec_keywords: set[str]) -> float:
    """Return a simple relevance score for *cv_text* against *spec_keywords*.

    The function tokenises the CV text into words (lower‑cased) and counts
    how many of the specification keywords appear.  The raw count is
    normalised by the total number of unique words in the CV to produce a
    value between 0 and 1.

    Parameters
    ----------
    cv_text:
        Raw text extracted from a CV document.
    spec_keywords:
        Set of lower‑cased keywords derived from the job specification.
    """
    words = {w.lower() for w in cv_text.split() if len(w) > 2}
    if not words:
        return 0.0
    match_count = sum(1 for kw in spec_keywords if kw in words)
    return match_count / len(words)
