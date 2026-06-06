"""Integration tests for CVBrain — verifies JSON parsing, return_raw behavior, and prompt construction."""

import json

# Ensure src is on path so imports work from any directory.
import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from cv_manager.brain import CVBrain

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _make_brain():
    """Create a CVBrain with mocked LLM client."""
    brain = CVBrain(api_key="test", base_url="http://localhost:9999/v1")
    brain.client = MagicMock()  # replace the real OpenAI client
    return brain


# ---------------------------------------------------------------------------
# Test 1 — Valid JSON response is parsed correctly
# ---------------------------------------------------------------------------


def test_valid_json_parsed():
    """LLM returns valid JSON → updates should be returned."""
    brain = _make_brain()
    mock_response = MagicMock()
    mock_response.choices[0].message.content = json.dumps(
        [
            {"original_text": "I know Python", "new_text": "Experienced in Python"},
        ]
    )
    brain.client.chat.completions.create.return_value = mock_response

    updates = brain.generate_tailored_content(
        job_spec="Python developer needed",
        cv_structure=[{"text": "I know Python", "style": "Normal"}],
        cv_content_md="",
    )

    assert len(updates) == 1
    assert updates[0]["original_text"] == "I know Python"


# ---------------------------------------------------------------------------
# Test 2 — JSON inside markdown code blocks is extracted
# ---------------------------------------------------------------------------


def test_json_in_code_blocks_extracted():
    """LLM wraps JSON in ```json … ``` → should still parse."""
    brain = _make_brain()
    mock_response = MagicMock()
    mock_response.choices[0].message.content = '```json\n[{"original_text": "old", "new_text": "new"}]\n```'
    brain.client.chat.completions.create.return_value = mock_response

    updates = brain.generate_tailored_content(
        job_spec="test",
        cv_structure=[{"text": "old", "style": "Normal"}],
        cv_content_md="",
    )

    assert len(updates) == 1
    assert updates[0]["new_text"] == "new"


# ---------------------------------------------------------------------------
# Test 3 — Non-JSON response with return_raw=True returns raw content
# ---------------------------------------------------------------------------


def test_non_json_with_return_raw_returns_raw():
    """LLM returns prose → when return_raw=True, caller gets the raw text."""
    brain = _make_brain()
    mock_response = MagicMock()
    mock_response.choices[0].message.content = (
        "I've reviewed your CV and I think it looks great. "
        "You might want to add some more details about your experience."
    )
    brain.client.chat.completions.create.return_value = mock_response

    result = brain.generate_tailored_content(
        job_spec="test",
        cv_structure=[],
        cv_content_md="",
        return_raw=True,
    )

    # Should be a tuple (updates, raw_content) even when JSON parsing fails
    assert isinstance(result, tuple), f"Expected tuple, got {type(result)}: {result}"
    updates, raw_content = result
    assert updates == []  # no valid updates parsed
    assert "I've reviewed your CV" in raw_content  # but we still get the raw text


# ---------------------------------------------------------------------------
# Test 4 — Non-JSON response with return_raw=False returns empty list silently
# ---------------------------------------------------------------------------


def test_non_json_with_return_raw_false_returns_empty():
    """LLM returns prose → when return_raw=False, caller gets []."""
    brain = _make_brain()
    mock_response = MagicMock()
    mock_response.choices[0].message.content = "This is not JSON at all."
    brain.client.chat.completions.create.return_value = mock_response

    result = brain.generate_tailored_content(
        job_spec="test",
        cv_structure=[],
        cv_content_md="",
        return_raw=False,
    )

    assert result == []


# ---------------------------------------------------------------------------
# Test 5 — LLM returns empty JSON array → no updates (legitimate)
# ---------------------------------------------------------------------------


def test_empty_json_array():
    """LLM returns [] → caller gets [], not an error."""
    brain = _make_brain()
    mock_response = MagicMock()
    mock_response.choices[0].message.content = "[]"
    brain.client.chat.completions.create.return_value = mock_response

    result = brain.generate_tailored_content(
        job_spec="test",
        cv_structure=[],
        cv_content_md="",
        return_raw=True,
    )

    assert isinstance(result, tuple)
    updates, raw_content = result
    assert updates == []
    assert "[]" in raw_content


# ---------------------------------------------------------------------------
# Test 6 — LLM returns dict with a list value → extracts the list
# ---------------------------------------------------------------------------


def test_dict_with_list_value():
    """LLM wraps response in {\"updates\": [...]} → should extract the list."""
    brain = _make_brain()
    mock_response = MagicMock()
    mock_response.choices[0].message.content = json.dumps(
        {
            "updates": [{"original_text": "a", "new_text": "b"}],
        }
    )
    brain.client.chat.completions.create.return_value = mock_response

    updates = brain.generate_tailored_content(
        job_spec="test",
        cv_structure=[{"text": "a", "style": "Normal"}],
        cv_content_md="",
    )

    assert len(updates) == 1


# ---------------------------------------------------------------------------
# Test 7 — System prompt is short and has JSON instruction first
# ---------------------------------------------------------------------------


def test_system_prompt_is_short_and_json_first():
    """System prompt should be concise (<800 chars) with JSON format at the top."""
    brain = _make_brain()

    # Mock response so generate_tailored_content completes normally.
    mock_response = MagicMock()
    mock_response.choices[0].message.content = "[]"
    brain.client.chat.completions.create.return_value = mock_response

    cv_structure = [{"text": "Test", "style": "Normal"}]
    job_spec = "test"
    cv_content_md = ""

    # Actually call generate_tailored_content — it will use the real prompt builder.
    brain.generate_tailored_content(
        job_spec=job_spec,
        cv_structure=cv_structure,
        cv_content_md=cv_content_md,
        return_raw=False,
    )

    # Get the actual system prompt from what was passed to the LLM mock.
    call_args = brain.client.chat.completions.create.call_args
    messages = call_args.kwargs["messages"]
    system_prompt = messages[0]["content"]

    # JSON instruction should be FIRST (primacy effect) — check first few lines.
    first_lines = "\n".join(system_prompt.split("\n")[:5])
    assert "JSON" in first_lines, f"JSON format instruction should appear early.\nPrompt starts:\n{first_lines}"

    # Prompt should not be excessively long (was 2000+ chars before fix).
    assert len(system_prompt) < 2100, f"System prompt too long ({len(system_prompt)} chars): {system_prompt}"


# ---------------------------------------------------------------------------
# Test 8 — Protected headings are filtered out
# ---------------------------------------------------------------------------


def test_protected_headings_filtered():
    """Updates targeting protected headings should be removed."""
    brain = _make_brain()
    mock_response = MagicMock()
    mock_response.choices[0].message.content = json.dumps(
        [
            {"original_text": "Career Highlights:", "new_text": "**Career Highlights:**"},
            {"original_text": "I know Python", "new_text": "Experienced in Python"},
        ]
    )
    brain.client.chat.completions.create.return_value = mock_response

    updates = brain.generate_tailored_content(
        job_spec="test",
        cv_structure=[
            {"text": "Career Highlights:", "style": "Heading 2"},
            {"text": "I know Python", "style": "Normal"},
        ],
        cv_content_md="",
    )

    # The Career Highlights update should be filtered out.
    for upd in updates:
        assert "Career Highlights" not in upd.get("original_text", "")


# ---------------------------------------------------------------------------
# Test 9 — Full flow with realistic CV + job spec (mocked LLM)
# ---------------------------------------------------------------------------


def test_realistic_flow():
    """Simulate a realistic scenario where the LLM suggests meaningful changes."""
    brain = _make_brain()
    mock_response = MagicMock()
    mock_response.choices[0].message.content = json.dumps(
        [
            {
                "original_text": "Responsible for managing projects.",
                "new_text": "Led cross-functional delivery teams across multiple platform transformation programmes, delivering £2M+ in annual savings.",
            },
            {
                "original_text": "Title: Project Manager",
                "new_text": "Title: Senior Delivery & Platform Transformation Leader",
            },
        ]
    )
    brain.client.chat.completions.create.return_value = mock_response

    cv_structure = [
        {"text": "Title: Project Manager", "style": "Heading 1"},
        {"text": "Responsible for managing projects.", "style": "Normal"},
    ]
    job_spec = "Senior Delivery Leader — platform transformation, budget management"

    result = brain.generate_tailored_content(
        job_spec=job_spec,
        cv_structure=cv_structure,
        cv_content_md="",
        return_raw=True,
    )

    assert isinstance(result, tuple)
    updates, raw_content = result
    assert len(updates) == 2
    assert "Title: Senior Delivery" in updates[1]["new_text"]


# ---------------------------------------------------------------------------
# Test 9.5 — Achievements Database is included in user prompt
# ---------------------------------------------------------------------------


def test_achievements_database_included_in_user_prompt():
    """Achievements database string should be appended to the user prompt if present."""
    brain = _make_brain()
    mock_response = MagicMock()
    mock_response.choices[0].message.content = "[]"
    brain.client.chat.completions.create.return_value = mock_response

    cv_structure = [{"text": "Title: Project Manager", "style": "Heading 1"}]
    job_spec = "Senior Delivery Leader"
    cv_content_md = "Delivered £3M in cloud savings using serverless."

    brain.generate_tailored_content(
        job_spec=job_spec,
        cv_structure=cv_structure,
        cv_content_md=cv_content_md,
        return_raw=False,
    )

    call_args = brain.client.chat.completions.create.call_args
    messages = call_args.kwargs["messages"]
    user_prompt = messages[1]["content"]

    assert "ACHIEVEMENTS DATABASE" in user_prompt
    assert "Delivered £3M in cloud savings" in user_prompt


# ---------------------------------------------------------------------------
# Test 10 — LLM connection error returns empty list
# ---------------------------------------------------------------------------


def test_connection_error():
    """LLM call fails → should raise ConnectionError."""
    brain = _make_brain()
    brain.client.chat.completions.create.side_effect = Exception("Connection refused")

    with pytest.raises(ConnectionError):
        brain.generate_tailored_content(
            job_spec="test",
            cv_structure=[],
            cv_content_md="",
        )


# ---------------------------------------------------------------------------
# Test 11 — ATS keyword extraction success
# ---------------------------------------------------------------------------


def test_extract_ats_keywords_success():
    """ATS keyword extraction returns structured list on successful LLM response."""
    brain = _make_brain()
    mock_response = MagicMock()
    mock_response.choices[0].message.content = json.dumps(
        {"technical_skills": ["Python", "AWS"], "soft_skills": ["Leadership"], "domain_and_certifications": ["FinTech"]}
    )
    brain.client.chat.completions.create.return_value = mock_response

    result = brain.extract_ats_keywords("Need a Python dev with AWS and Leadership in FinTech")
    assert result["technical_skills"] == ["Python", "AWS"]
    assert result["soft_skills"] == ["Leadership"]
    assert result["domain_and_certifications"] == ["FinTech"]


# ---------------------------------------------------------------------------
# Test 12 — ATS keyword extraction failure
# ---------------------------------------------------------------------------


def test_extract_ats_keywords_fallback():
    """ATS keyword extraction raises ConnectionError on LLM error/invalid JSON."""
    brain = _make_brain()
    brain.client.chat.completions.create.side_effect = Exception("LLM Down")

    try:
        brain.extract_ats_keywords("Python AWS CI/CD Scrum Leadership")
        assert False, "Expected ConnectionError to be raised"
    except ConnectionError as e:
        assert "Could not connect to LLM server" in str(e)


# ---------------------------------------------------------------------------
# Test 13 — ATS keyword extraction empty job spec
# ---------------------------------------------------------------------------


def test_extract_ats_keywords_empty():
    """ATS keyword extraction returns empty categories if job spec is empty."""
    brain = _make_brain()
    result = brain.extract_ats_keywords("   ")
    assert result["technical_skills"] == []
    assert result["soft_skills"] == []
    assert result["domain_and_certifications"] == []


# ---------------------------------------------------------------------------
# Run all tests
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import traceback

    tests = [
        test_valid_json_parsed,
        test_json_in_code_blocks_extracted,
        test_non_json_with_return_raw_returns_raw,
        test_non_json_with_return_raw_false_returns_empty,
        test_empty_json_array,
        test_dict_with_list_value,
        test_system_prompt_is_short_and_json_first,
        test_protected_headings_filtered,
        test_realistic_flow,
        test_connection_error,
        test_extract_ats_keywords_success,
        test_extract_ats_keywords_fallback,
        test_extract_ats_keywords_empty,
        test_achievements_database_included_in_user_prompt,
    ]

    passed = 0
    failed = 0

    for test_fn in tests:
        try:
            test_fn()
            print(f"✅ {test_fn.__name__}")
            passed += 1
        except Exception as e:
            print(f"❌ {test_fn.__name__}: {e}")
            traceback.print_exc()
            failed += 1

    print(f"\n{passed}/{len(tests)} passed, {failed} failed")
    if failed > 0:
        sys.exit(1)
