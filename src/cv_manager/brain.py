import json
import logging
import os
import re
import difflib
from openai import OpenAI
from typing import List, Dict, Any, Callable, Optional
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

logger = logging.getLogger(__name__)


def generate_cv_content(
    system_prompt: str,
    user_prompt: str,
    provider: str,
    api_key: Optional[str] = None,
    base_url: Optional[str] = None,
    model: Optional[str] = None,
    timeout: float = 15.0,
    client: Optional[OpenAI] = None
) -> str:
    """
    Unified router function to call LLM providers (Local, DeepSeek, Grok).
    """
    provider_lower = provider.lower()

    if provider_lower == "deepseek":
        target_api_key = os.getenv("DEEPSEEK_API_KEY")
        if not target_api_key:
            raise ValueError("DeepSeek API key is missing. Please set the DEEPSEEK_API_KEY environment variable in your .env file.")
        target_base_url = "https://api.deepseek.com"
        target_model = "deepseek-chat"
        target_timeout = 15.0
    elif provider_lower == "grok":
        target_api_key = os.getenv("XAI_API_KEY")
        if not target_api_key:
            raise ValueError("Grok API key is missing. Please set the XAI_API_KEY environment variable in your .env file.")
        target_base_url = "https://api.x.ai/v1"
        target_model = "grok-4.3"
        target_timeout = 15.0
    elif provider_lower == "local":
        target_api_key = api_key or os.getenv("OPENAI_API_KEY") or "lm-studio"
        target_base_url = base_url or "http://localhost:1234/v1"
        target_model = model or os.getenv("LM_STUDIO_MODEL") or "llama-3.1-8b-instruct"
        target_timeout = timeout
    else:
        raise ValueError(f"Unknown LLM provider: {provider}")

    # Use the provided client if present (useful for unit tests mocking brain.client)
    if provider_lower == "local" and client is not None:
        use_client = client
    else:
        use_client = OpenAI(api_key=target_api_key, base_url=target_base_url)

    try:
        response = use_client.chat.completions.create(
            model=target_model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0,
            timeout=target_timeout
        )
        return response.choices[0].message.content
    except Exception as e:
        logger.error(f"LLM request failed using provider {provider}: {e}")
        raise ConnectionError(f"Could not connect to LLM server ({target_base_url}). Please check your settings: {e}") from e



class CVBrain:
    """Handles the intelligent part of CV tailoring using an LLM."""

    def __init__(self, api_key: str = None, base_url: str = None, model: str = None, timeout: float = 60.0, provider: str = "Local"):
        # Fallback to environment variable or hardcoded LM Studio defaults
        self.api_key = api_key or os.getenv("OPENAI_API_KEY") or "lm-studio"
        self.base_url = base_url or "http://localhost:1234/v1"
        # If no model specified, use the one currently loaded in LM Studio (default: "llama-3.1-8b-instruct").
        self.model = model or os.getenv("LM_STUDIO_MODEL") or "llama-3.1-8b-instruct"
        self.timeout = timeout
        self.provider = provider

        self.client = OpenAI(api_key=self.api_key, base_url=self.base_url)

    def generate_tailored_content(
        self,
        job_spec: str,
        cv_structure: List[Dict[str, Any]],
        cv_content_md: str,
        return_raw: bool = False,
        matched_keywords: Optional[List[str]] = None
    ) -> List[Dict[str, Any]] | tuple[List[Dict[str, Any]], Optional[str]]:
        """
        Uses LLM to decide which parts of the CV to update and what the new text should be.
        Returns a list of updates: [{'original_text': '...', 'new_text': '...'}]
        """

        # Load the writing style guide from JSON if it exists.
        try:
            prompt_path = os.path.join(os.path.dirname(__file__), "prompts", "writing_style.json")
            with open(prompt_path, encoding="utf-8") as f:
                style_data = json.load(f)

            # Build a SHORT system-prompt — smaller models ignore instructions buried in long prompts.
            # KEY RULES go FIRST (primacy effect), constraints last (recency bias).
            parts = [
                "### FORMAT INSTRUCTION (MOST IMPORTANT)",
                "Return response ONLY as valid JSON list of objects with keys 'original_text' and 'new_text'.",
                "Do NOT include explanation, markdown formatting, or text outside the JSON.",
                "",

                "### ROLE",
                f"You are a professional CV editor. Use {style_data.get('language', {}).get('spelling', 'UK English')} spelling.",
                "Tailor candidate's CV to match job spec by aligning terminology and emphasizing relevant experience.",
                "",

                "### WRITING STYLE (STAR / IMPACT-FIRST)",
                "1. Format: Action Verb → Scope/Context → Strategic Purpose → Quantified Outcome.",
                "2. Lead with impact/outcomes first (e.g. 'Reduced deploys by 40% by implementing...' vs 'Responsible for...').",
                "3. Use confident senior professional tone with lived detail. Avoid generic buzzwords.",
                "4. Align CV phrasing with job spec terminology without altering underlying facts.",
                "",

                "### STRICT CONSTRAINTS (ZERO HALLUCINATION TOLERANCE)",
                "1. Every 'original_text' MUST be an exact, word-for-word match from the CV.",
                "2. You are a FACTUAL editor, not a creative writer. Do NOT invent, assume, or extrapolate any projects, numbers, percentages, client names, team sizes, certifications, tools, or dates.",
                "3. Use ONLY facts and metrics explicitly present in CURRENT CV CONTENT or the ACHIEVEMENTS DATABASE. If a metric or detail is not written there, you do not know it and cannot use it.",
                "4. If a keyword or skill requested in the job description is missing from both the CV and Achievements Database, do NOT add it. Omit it. Never add a technology or responsibility the candidate has not actually used or held.",
                "5. Do NOT upgrade or change job titles (except the top CV title) or dates of employment.",
            ]

            # Section order — one line, high value.
            struct = style_data.get("structure", {})
            order = struct.get("order", [])
            if order:
                parts.append(f"Section order: {' → '.join(order)}.")

            # Flag words — keep the full list, compacted to one line.
            vocab = style_data.get("ai_sounding_vocabulary_check", {}).get("flag_and_replace", [])
            if vocab:
                parts.append(f"Do not use these words: {', '.join(vocab)}.")

            system_prompt = "\n".join(parts)
        except (FileNotFoundError, json.JSONDecodeError):
            # Fallback to minimal prompt if JSON is missing or invalid.
            system_prompt = (
                "You are a professional CV editor. Use UK English. Follow the section order: summary → expertise → highlights → experience → education → interests.\n"
                "DO NOT invent new experiences, dates, or job titles. Return your response ONLY as a valid JSON list of objects."
            )

        # Build a human-readable CV text from the structure for better LLM comprehension.
        cv_text_lines: List[str] = []
        current_section = "General"
        for elem in cv_structure:
            style = elem.get("style", "")
            is_heading = elem.get("is_heading", False)
            text = elem.get("text", "")
            if not text:
                continue
            # Detect section headings (e.g., "Professional Experience:", "Education:")
            if is_heading or text.endswith(":"):
                current_section = text.rstrip(":")
            cv_text_lines.append(f"[{current_section}] {text}")
        cv_text = "\n".join(cv_text_lines)

        user_prompt = (
            f"### JOB SPECIFICATION:\n{job_spec}\n\n"
            f"### CURRENT CV CONTENT:\n{cv_text}\n\n"
        )
        
        if cv_content_md.strip():
            user_prompt += (
                f"### ACHIEVEMENTS DATABASE (FACT POOL):\n"
                f"Use the following additional details, achievements, and facts to help enrich and tailor the CV bullet points. "
                f"Do not invent facts outside of this list and the current CV:\n{cv_content_md}\n\n"
            )
            
        if matched_keywords:
            user_prompt += (
                f"### KEYWORD GAP ANALYSIS:\n"
                f"The following keywords/skills from the job specification are currently missing or weak in the CV. "
                f"Attempt to incorporate them using details from the Achievements Database or existing CV facts:\n{', '.join(matched_keywords)}\n\n"
            )
            
        user_prompt += (
            "### WARNING AGAINST HALLUCINATION:\n"
            "Do NOT invent any facts, project details, metrics, or technologies. "
            "If a keyword cannot be backed up by facts in the ACHIEVEMENTS DATABASE or CURRENT CV CONTENT, simply do not mention it. "
            "Your output must contain only rephrasings and alignments of existing facts. "
            "Failure to obey this constraint will make the CV invalid.\n\n"
            "Identify specific paragraphs in the CURRENT CV CONTENT that should be updated to better align with the job spec.\n"
            "For each update, provide the exact original text and the new, improved text.\n\n"
            "Additionally, update the CV title (if present, e.g. 'Title: ...') to match the job title in the job spec.\n\n"
            "Return format: [{'original_text': '...', 'new_text': '...'}]"
        )

        # Use the unified router function to call the LLM
        try:
            raw_content = generate_cv_content(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                provider=self.provider,
                api_key=self.api_key,
                base_url=self.base_url,
                model=self.model,
                timeout=self.timeout,
                client=self.client
            )
        except Exception as e:
            logger.error(f"ERROR: LLM call failed: {e}")
            raise e

        # Try to extract JSON from markdown code blocks if present.
        json_match = re.search(r'```(?:json)?\s*(.*?)\s*```', raw_content, re.DOTALL)
        extracted = json_match.group(1).strip() if json_match else None

        data = None
        # Try direct parsing first (most reliable), then code-block extraction as fallback.
        for candidate in [raw_content.strip(), extracted]:
            try:
                data = json.loads(candidate or "")
                break
            except json.JSONDecodeError:
                continue

        if data is None:
            logger.error("LLM returned non-JSON content:\n%s", raw_content)
            if return_raw:
                return [], raw_content
            return []

        # Handle different possible structures returned by the model
        if isinstance(data, dict):
            updates = []
            for key, val in data.items():
                if isinstance(val, list):
                    updates = val
                    break
        elif isinstance(data, list):
            updates = data
        else:
            return []

        # Auto‑insert job title if the LLM didn't include one
        title_found = any(
            u.get("original_text", "").startswith("Title:") for u in updates
        )
        if not title_found:
            match = re.search(r"(?i)job\s*title[:\s]+(.+)", job_spec)
            new_title = match.group(1).strip() if match else None
            if new_title:
                for elem in cv_structure:
                    txt = elem.get("text", "")
                    if txt.startswith("Title:"):
                        updates.append({"original_text": txt, "new_text": f"Title: {new_title}"})
                        break

        # Strip section prefixes (e.g. [General] or **[General]**) and markdown bold from headings only.
        section_prefix_re = re.compile(r"^\[[^\]]+\]\s*")
        bold_section_prefix_re = re.compile(r"^\*\*\[[^\]]+\]\*\*\s*")
        heading_re = re.compile(r'^(\*\*[^*]+)\*\*')
        for upd in updates:
            if "original_text" in upd:
                text = upd["original_text"].strip()
                text = bold_section_prefix_re.sub("", text)
                text = section_prefix_re.sub("", text)
                text = heading_re.sub(r'\1', text)
                upd["original_text"] = text
            if "new_text" in upd:
                text = upd["new_text"].strip()
                text = bold_section_prefix_re.sub("", text)
                text = section_prefix_re.sub("", text)
                text = heading_re.sub(r'\1', text)
                upd["new_text"] = text

        # Remove any update that targets generic headings (exact match after stripping leading whitespace).
        protected_headings = {"Career Highlights:", "Areas of Expertise:"}
        updates = [u for u in updates if not (
            u.get("original_text", "").strip() in protected_headings or
            u.get("new_text", "").strip() in protected_headings
        )]

        # Validate: every original_text MUST exist in the actual CV content.
        # This prevents the LLM from hallucinating text that isn't in the document.
        # We normalize texts to avoid false rejections due to spacing, dashes, casing, or minor spelling mismatches.
        def clean_text(t: str) -> str:
            t = re.sub(r"\s+", " ", t)
            return t.strip().strip(".,;:?!-–—•*\"'").lower()

        # Build list of normalized CV paragraphs and full content
        cv_paras_norm = [clean_text(elem.get("text", "")) for elem in cv_structure if elem.get("text", "")]
        cv_content_norm = clean_text(cv_content_md)
        cv_all_text_norm = clean_text(" ".join(elem.get("text", "") for elem in cv_structure) + "\n" + cv_content_md)

        valid_updates = []
        for upd in updates:
            orig = upd.get("original_text", "").strip()
            if not orig:
                continue
            orig_norm = clean_text(orig)

            found = False
            # 1. Check if it matches any CV paragraph exactly (normalized)
            if orig_norm in cv_paras_norm or orig_norm == cv_content_norm:
                found = True
            # 2. Check if it's a substring of the overall CV content
            elif orig_norm in cv_all_text_norm:
                found = True
            # 3. Check if there's a highly similar paragraph (>= 80% similarity)
            if not found and len(orig_norm) >= 15:
                for p_norm in cv_paras_norm:
                    if difflib.SequenceMatcher(None, orig_norm, p_norm).ratio() >= 0.80:
                        found = True
                        break

            if not found:
                logger.warning("DROPPED hallucinated update — original_text not in CV: %s", orig[:80])
            else:
                valid_updates.append(upd)
        updates = valid_updates

        logger.info("LLM returned %d update(s): %s", len(updates), updates)

        if return_raw:
            return updates, raw_content
        return updates

    def extract_ats_keywords(self, job_spec: str) -> Dict[str, List[str]]:
        """
        Uses LLM to extract key ATS keywords (skills, technologies, certifications) from a job description.
        Returns a dict:
        {
            "technical_skills": [...],
            "soft_skills": [...],
            "domain_and_certifications": [...]
        }
        """
        if not job_spec.strip():
            return {
                "technical_skills": [],
                "soft_skills": [],
                "domain_and_certifications": []
            }

        system_prompt = (
            "You are an expert ATS (Applicant Tracking System) parser.\n"
            "Analyze the job specification and extract the core keywords and requirements.\n"
            "Respond ONLY with a valid JSON object matching the following structure:\n"
            "{\n"
            "  \"technical_skills\": [\"Programming languages, frameworks, databases, tools, hardware, tech platforms, etc.\"],\n"
            "  \"soft_skills\": [\"Leadership, communication, methodology like Agile/Scrum, stakeholder management, delivery, etc.\"],\n"
            "  \"domain_and_certifications\": [\"Certifications like PRINCE2, PMP, AWS Certified, or domain expertise like FinTech, Cyber Security, etc.\"]\n"
            "}\n"
            "Do NOT include any markdown code blocks, explanation, or commentary outside the JSON."
        )

        user_prompt = f"### JOB SPECIFICATION:\n{job_spec}\n"

        try:
            raw_content = generate_cv_content(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                provider=self.provider,
                api_key=self.api_key,
                base_url=self.base_url,
                model=self.model,
                timeout=self.timeout,
                client=self.client
            )
        except Exception as e:
            logger.error("LLM call failed during ATS keyword extraction: %s", e)
            raise e

        # Try to parse JSON. Use regex to extract JSON blocks if the model wrapped it in code blocks.
        json_match = re.search(r'```(?:json)?\s*(.*?)\s*```', raw_content, re.DOTALL)
        extracted = json_match.group(1).strip() if json_match else None

        data = None
        for candidate in [raw_content.strip(), extracted]:
            try:
                data = json.loads(candidate or "")
                break
            except json.JSONDecodeError:
                continue

        if not isinstance(data, dict):
            logger.warning("LLM returned non-JSON or invalid structure for ATS keywords.")
            raise ValueError("LLM response did not contain a valid JSON object of ATS keywords.")

        # Normalize and validate keys
        result = {
            "technical_skills": [str(x).strip() for x in data.get("technical_skills", []) if str(x).strip()],
            "soft_skills": [str(x).strip() for x in data.get("soft_skills", []) if str(x).strip()],
            "domain_and_certifications": [str(x).strip() for x in data.get("domain_and_certifications", []) if str(x).strip()]
        }
        return result


    def generate_diff(self, job_spec: str, cv_structure: List[Dict[str, Any]], cv_content_md: str) -> str:
        updates = self.generate_tailored_content(job_spec, cv_structure, cv_content_md)
        if not updates:
            return "No changes detected."

        lines: List[str] = []
        for upd in updates:
            original = upd.get("original_text", "")
            new = upd.get("new_text", "")
            diff = difflib.unified_diff(
                [original + "\n"],
                [new + "\n"],
                fromfile="src/cv_manager/data/CvContent.md",
                tofile="src/cv_manager/data/CvContent.md",
                lineterm=""
            )
            lines.extend(diff)
        return "\n".join(lines) if lines else "No changes detected."


if __name__ == "__main__":
    try:
        brain = CVBrain()
        test_updates = brain.generate_tailored_content(
            "Looking for a Python developer with experience in Streamlit.",
            [{"text": "I know Python", "style": "Normal"}],
            "I have built many web apps using Streamlit and FastAPI."
        )
        print(test_updates)
    except Exception as e:
        print(f"Test failed: {e}")