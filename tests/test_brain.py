"""Unit tests for :pyclass:`cv_manager.brain.CVBrain`.

The real implementation talks to an LLM.  For unit testing we monkey‑patch the
``client.chat.completions.create`` method so that no external network call is
made and a deterministic response is returned.
"""

import json
from types import SimpleNamespace

import pytest

from cv_manager.brain import CVBrain


def _mock_response(content: str):
    """Return a minimal object mimicking the OpenAI response structure.

    The real SDK returns ``response.choices[0].message.content``.  We create a
    simple nested namespace that provides this attribute chain.
    """

    return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content=content))])


@pytest.fixture
def brain(monkeypatch):
    """Return a :class:`CVBrain` instance with the LLM call mocked.

    The mock simply returns a JSON list of two updates.  This is enough to test
    that the parsing logic works correctly.
    """

    brain = CVBrain()

    # Patch the client so no real HTTP request is made.
    def _create(*_, **__):
        content = json.dumps(
            [
                {"original_text": "I know Python", "new_text": "Proficient in Python"},
                {"original_text": "FastAPI", "new_text": "Experience with FastAPI"},
            ]
        )
        return _mock_response(content)

    monkeypatch.setattr(brain.client.chat.completions, "create", _create)
    return brain


def test_generate_tailored_content_success(brain):
    job_spec = "Python developer with Streamlit"
    cv_structure = [{"text": "I know Python", "style": "Normal"}]
    cv_content_md = "Built many web apps using Streamlit and FastAPI."

    updates = brain.generate_tailored_content(job_spec, cv_structure, cv_content_md)
    assert isinstance(updates, list)
    assert len(updates) == 2
    assert updates[0]["original_text"] == "I know Python"
    assert updates[0]["new_text"] == "Proficient in Python"


def test_generate_tailored_content_invalid_json(brain, monkeypatch):
    # Simulate the LLM returning malformed JSON.
    def _create(*_, **__):
        return _mock_response("{invalid json}")

    monkeypatch.setattr(brain.client.chat.completions, "create", _create)
    updates = brain.generate_tailored_content("spec", [], "")
    assert updates == []  # function should swallow the error and return empty list
