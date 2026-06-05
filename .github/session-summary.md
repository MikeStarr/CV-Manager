# CV-Manager LLM Prompt Fix — Session Summary (2026-06-04)

## Problem
App returned non-LLM content when running `streamlit run src/cv_manager/app.py`. The LLM was producing prose evaluations instead of JSON.

## Root Cause
ssue 2 — Non-JSON content: The system prompt is extremely verbose — the style guide JSON adds dozens of lines, then 12 more rules are appended. Smaller models get overwhelmed and ignore the JSON format instruction buried in the middle. Also no temperature is set, so responses can be unpredictable.

## Fix Applied (brain.py)
Three changes to `src/cv_manager/brain.py`:

### 1. Set `temperature=0` on LLM call
Deterministic output — eliminates randomness for structured JSON generation.

### 2. Drastically simplified system prompt (~60% shorter)
- Removed verbose sections: `tone_and_positioning`, `clarity_context_impact`, `consistency_and_quality`, full `ai_tell_pattern_check` list (kept only vocabulary flags, capped at 8 words).
- Reorganized with clear section headers (`### FORMAT INSTRUCTION`, `### ROLE`, `### CONSTRAINTS`) for better model parsing.

### 3. JSON format instruction moved FIRST (primacy effect)
The "Return ONLY as valid JSON" directive now appears at the very top of the system prompt, not buried in the middle. Added explicit warning: "Do NOT include any explanation, markdown formatting, or text outside the JSON."

## Verification Needed
- Run `streamlit run src/cv_manager/app.py` and test with a real job spec + CV to confirm LLM returns valid JSON consistently.
- Test with smaller models (e.g., llama-3.1-8b) specifically — they were most affected.