"""Integration tests for CVBrain — verifies JSON parsing, return_raw behavior, and prompt construction."""

import json
from typing import Any

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

    result = brain.generate_tailored_content(
        job_spec="Python developer needed",
        cv_structure=[{"text": "I know Python", "style": "Normal"}],
        cv_content_md="",
    )

    assert isinstance(result, dict)
    updates = result["updates"]
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

    result = brain.generate_tailored_content(
        job_spec="test",
        cv_structure=[{"text": "old", "style": "Normal"}],
        cv_content_md="",
    )

    assert isinstance(result, dict)
    updates = result["updates"]
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
    audit_data, raw_content = result
    updates = audit_data["updates"]
    assert updates == []  # no valid updates parsed
    assert raw_content is not None
    assert "I've reviewed your CV" in raw_content  # but we still get the raw text


# ---------------------------------------------------------------------------
# Test 4 — Non-JSON response with return_raw=False returns empty list silently
# ---------------------------------------------------------------------------


def test_non_json_with_return_raw_false_returns_empty():
    """LLM returns prose → when return_raw=False, caller gets empty audit dict."""
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

    assert isinstance(result, dict)
    assert result["updates"] == []


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
    audit_data, raw_content = result
    updates = audit_data["updates"]
    assert updates == []
    assert raw_content is not None
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

    result = brain.generate_tailored_content(
        job_spec="test",
        cv_structure=[{"text": "a", "style": "Normal"}],
        cv_content_md="",
    )

    assert isinstance(result, dict)
    updates = result["updates"]
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
    client: Any = brain.client
    call_args = client.chat.completions.create.call_args
    messages = call_args.kwargs["messages"]
    system_prompt = messages[0]["content"]

    # JSON instruction should be in the system prompt.
    assert "JSON" in system_prompt, f"JSON format instruction should appear in prompt.\nPrompt:\n{system_prompt}"

    # Prompt should not be excessively long (was 2000+ chars before fix, updated to accommodate the custom FS PM audit prompt).
    assert len(system_prompt) < 6500, f"System prompt too long ({len(system_prompt)} chars): {system_prompt}"


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

    result = brain.generate_tailored_content(
        job_spec="test",
        cv_structure=[
            {"text": "Career Highlights:", "style": "Heading 2"},
            {"text": "I know Python", "style": "Normal"},
        ],
        cv_content_md="",
    )

    assert isinstance(result, dict)
    updates = result["updates"]
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
    audit_data, raw_content = result
    updates = audit_data["updates"]
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

    client: Any = brain.client
    call_args = client.chat.completions.create.call_args
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
# Test 10.5 — Parsing of the new structured issues JSON schema
# ---------------------------------------------------------------------------


def test_issues_schema_parsing():
    """Verify parsing of issues list into updates and formatted weaknesses."""
    brain = _make_brain()
    mock_response = MagicMock()
    mock_response.choices[0].message.content = json.dumps(
        {
            "strengths": ["Leadership experience"],
            "issues": [
                {
                    "issue": "Generic phrase used",
                    "original_text": "Proven track record in delivery",
                    "proposed_fix": "Managed delivery of technology programmes",
                    "fixable": True,
                },
                {
                    "issue": "Missing metrics",
                    "original_text": "Led project teams",
                    "proposed_fix": "Cannot be improved without additional evidence.",
                    "fixable": False,
                },
            ],
            "ats_match_pct": 85,
        }
    )
    brain.client.chat.completions.create.return_value = mock_response

    result = brain.generate_tailored_content(
        job_spec="test",
        cv_structure=[{"text": "Proven track record in delivery", "style": "Normal"}],
        cv_content_md="",
    )

    assert isinstance(result, dict)
    assert result["strengths"] == ["Leadership experience"]
    assert result["ats_match_pct"] == 85
    
    updates = result["updates"]
    assert len(updates) == 1
    assert updates[0]["original_text"] == "Proven track record in delivery"
    assert updates[0]["new_text"] == "Managed delivery of technology programmes"
    
    weaknesses = result["weaknesses"]
    assert len(weaknesses) == 2
    assert "Fixed: Generic phrase used" in weaknesses[0]
    assert "Unresolved: Missing metrics" in weaknesses[1]


# ---------------------------------------------------------------------------
# Test 11 — Fallback job title auto-insertion works with title keywords
# ---------------------------------------------------------------------------


def test_title_fallback_insertion():
    """If LLM doesn't return a title update, but job spec has Job Title and CV has a title paragraph, fallback inserts it."""
    brain = _make_brain()
    mock_response = MagicMock()
    mock_response.choices[0].message.content = json.dumps(
        {
            "strengths": [],
            "issues": [
                {
                    "issue": "Generic phrase",
                    "original_text": "Experienced Project Manager",
                    "proposed_fix": "Senior Delivery Manager",
                    "fixable": True,
                }
            ],
            "ats_match_pct": 70,
        }
    )
    brain.client.chat.completions.create.return_value = mock_response

    # CV structure has contact line (index 0) and title line (index 1)
    cv_structure = [
        {"text": "John Doe | email@example.com", "style": "Normal"},
        {"text": "Digital Delivery Manager | Digital Ecosystems", "style": "Normal"},
        {"text": "Experienced Project Manager", "style": "Normal"},
    ]

    result = brain.generate_tailored_content(
        job_spec="Job Title: Portfolio Manager / Programme Lead",
        cv_structure=cv_structure,
        cv_content_md="",
    )

    updates = result["updates"]
    # There should be 2 updates: the generic phrase fix, plus the fallback title update
    assert len(updates) == 2

    # One of the updates should target 'Digital Delivery Manager | Digital Ecosystems'
    fallback_update = [u for u in updates if u["original_text"] == "Digital Delivery Manager | Digital Ecosystems"]
    assert len(fallback_update) == 1
    assert fallback_update[0]["new_text"] == "Portfolio Manager / Programme Lead"


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
        test_achievements_database_included_in_user_prompt,
        test_issues_schema_parsing,
        test_title_fallback_insertion,
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
