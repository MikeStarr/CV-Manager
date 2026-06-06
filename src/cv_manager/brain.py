import difflib
import json
import logging
import os
import re
from typing import Any, Literal, overload

from dotenv import load_dotenv
from openai import OpenAI

# Load environment variables
load_dotenv()

logger = logging.getLogger(__name__)


def generate_cv_content(
    system_prompt: str,
    user_prompt: str,
    provider: str,
    api_key: str | None = None,
    base_url: str | None = None,
    model: str | None = None,
    timeout: float = 15.0,
    client: OpenAI | None = None,
) -> str:
    """
    Unified router function to call LLM providers (Local, ChatGPT, DeepSeek, Grok).
    """
    provider_lower = provider.lower()

    if provider_lower == "deepseek":
        target_api_key = os.getenv("DEEPSEEK_API_KEY")
        if not target_api_key:
            raise ValueError(
                "DeepSeek API key is missing. Please set the DEEPSEEK_API_KEY environment variable in your .env file."
            )
        target_base_url = "https://api.deepseek.com"
        target_model = model or "deepseek-chat"
        target_timeout = timeout
    elif provider_lower == "grok":
        target_api_key = os.getenv("XAI_API_KEY")
        if not target_api_key:
            raise ValueError(
                "Grok API key is missing. Please set the XAI_API_KEY environment variable in your .env file."
            )
        target_base_url = "https://api.x.ai/v1"
        target_model = model or "grok-4.3"
        target_timeout = timeout
    elif provider_lower == "chatgpt":
        target_api_key = os.getenv("OPENAI_API_KEY")
        if not target_api_key:
            raise ValueError(
                "OpenAI API key is missing. Please set the OPENAI_API_KEY environment variable in your .env file."
            )
        target_base_url = "https://api.openai.com/v1"
        #target_model = model or "gpt-4o"
        target_model = model or "gpt-5.4"
        target_timeout = timeout
    elif provider_lower == "local":
        target_api_key = api_key or os.getenv("OPENAI_API_KEY") or "lm-studio"
        target_base_url = base_url or "http://localhost:1234/v1"
        target_model = model or os.getenv("LM_STUDIO_MODEL") or "llama-3.1-8b-instruct"
        target_timeout = timeout
    else:
        raise ValueError(f"Unknown LLM provider: {provider}")

    # Use the provided client if present (useful for unit tests mocking brain.client)
    if client is not None:
        use_client = client
    else:
        use_client = OpenAI(api_key=target_api_key, base_url=target_base_url)

    try:
        response = use_client.chat.completions.create(
            model=target_model,
            messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}],
            temperature=0,
            timeout=target_timeout,
        )
        return response.choices[0].message.content or ""
    except Exception as e:
        logger.error(f"LLM request failed using provider {provider}: {e}")
        raise ConnectionError(
            f"Could not connect to LLM server ({target_base_url}). Please check your settings: {e}"
        ) from e


class CVBrain:
    """Handles the intelligent part of CV tailoring using an LLM."""

    def __init__(
        self,
        api_key: str | None = None,
        base_url: str | None = None,
        model: str | None = None,
        timeout: float = 60.0,
        provider: str = "Local",
    ):
        self.provider = provider
        provider_lower = provider.lower()

        if provider_lower == "chatgpt":
            self.api_key = api_key or os.getenv("OPENAI_API_KEY") or ""
            self.base_url = base_url or "https://api.openai.com/v1"
            self.model = model or "gpt-4o"
        elif provider_lower == "deepseek":
            self.api_key = api_key or os.getenv("DEEPSEEK_API_KEY") or ""
            self.base_url = base_url or "https://api.deepseek.com"
            self.model = model or "deepseek-chat"
        elif provider_lower == "grok":
            self.api_key = api_key or os.getenv("XAI_API_KEY") or ""
            self.base_url = base_url or "https://api.x.ai/v1"
            self.model = model or "grok-4.3"
        else:
            self.api_key = api_key or os.getenv("OPENAI_API_KEY") or "lm-studio"
            self.base_url = base_url or "http://localhost:1234/v1"
            self.model = model or os.getenv("LM_STUDIO_MODEL") or "llama-3.1-8b-instruct"

        self.timeout = timeout
        self.client = OpenAI(api_key=self.api_key, base_url=self.base_url)

    @overload
    def generate_tailored_content(
        self,
        job_spec: str,
        cv_structure: list[dict[str, Any]],
        cv_content_md: str,
        return_raw: Literal[False] = False,
    ) -> dict[str, Any]:
        ...

    @overload
    def generate_tailored_content(
        self,
        job_spec: str,
        cv_structure: list[dict[str, Any]],
        cv_content_md: str,
        return_raw: Literal[True],
    ) -> tuple[dict[str, Any], str | None]:
        ...

    @overload
    def generate_tailored_content(
        self,
        job_spec: str,
        cv_structure: list[dict[str, Any]],
        cv_content_md: str,
        return_raw: bool,
    ) -> dict[str, Any] | tuple[dict[str, Any], str | None]:
        ...

    def generate_tailored_content(
        self,
        job_spec: str,
        cv_structure: list[dict[str, Any]],
        cv_content_md: str,
        return_raw: bool = False,
    ) -> dict[str, Any] | tuple[dict[str, Any], str | None]:
        """
        Uses LLM to decide which parts of the CV to update and what the new text should be.
        Returns an audit dict with strengths, weaknesses, match rate, and updates.
        """

        system_prompt = (
            "You are a senior CV strategist specialising in Technology, Financial Services, and Digital Delivery roles. Use UK English throughout.\n"
            "Task: Rewrite and reposition the candidate's CV to align with the job spec. You must review and tailor: the headline title (always match target role/seniority), professional summary, Areas of Expertise, Career Highlights, and work experience bullets. Extract ATS keywords, domain terms, and seniority signals, integrating them only when supported by candidate evidence. Do NOT invent achievements, metrics, or experience; only reframe, elevate, or reorganise existing evidence.\n\n"
            "You are authorised to:\n"
            "- restructure/rewrite bullets, headline title, sections\n"
            "- elevate/de-emphasise themes to match the job spec\n"
            "- reframe achievements to strengthen seniority/ownership\n"
            "- remove generic/consultant phrasing; ensure authentic human tone\n\n"
            "### ATS KEYWORD INTEGRATION\n"
            "1. Extract ATS keywords from job spec (responsibilities, skills, domain terms).\n"
            "2. Map and integrate keywords only when supported by candidate evidence.\n"
            "3. Rephrase bullets to naturally incorporate keywords; exclude unsupported ones.\n\n"
            "### ROLE-AGNOSTIC REPOSITIONING (Adapt emphasis based on job spec)\n"
            "- Governance-heavy: emphasise governance, PMO, control, reporting, risk, compliance.\n"
            "- Delivery-heavy: emphasise delivery leadership, alignment, execution, velocity, outcomes.\n"
            "- Technical: emphasise systems, platforms, architecture, engineering collaboration.\n"
            "- Product-aligned: emphasise roadmaps, prioritisation, stakeholder alignment, value.\n"
            "- Transformation-focused: emphasise frameworks, change, operating models, ways of working.\n\n"
            "### WRITING RULES\n"
            "- Use UK English throughout. No em-dashes.\n"
            "- Tone: direct, specific, and unimpressed with itself. Write like an experienced programme manager explaining their work to a peer — not selling it to a recruiter.\n"
            "- Every bullet must include at least one concrete detail: a number, a system name, a team size, a timeline, or a named constraint. If the bullet could belong to any PM at any company, it is not specific enough.\n"
            "- Never use adjectives that do not carry verifiable meaning. 'Large' is banned. '£20m' is not. 'Complex' is banned. '14 teams across three locations' is not.\n"
            "- Do not write like a LinkedIn post, a job advert, or a brochure. If the sentence sounds like sales copy, rewrite it.\n"
            "- RIGHT tone: 'Managed a £20m budget across 15 teams, holding variance to 1% while absorbing headcount cuts.'\n"
            "- WRONG tone: 'Spearheaded transformative cross-functional initiatives that leveraged cutting-edge delivery frameworks to empower stakeholders.'\n"
            "- Strictly avoid AI buzzwords (e.g., adept, skilled in, spearheaded, orchestrated, leveraged, synergy, foster, transformative, deep-dive, vibrant, results-oriented, game-changer, passionate, seamlessly, cutting-edge, dynamic, empower, strategic visionary, multifaceted, unwavering commitment, thought leader, at the intersection, strengthening, proven track record).\n\n"
            "### PROFESSIONAL SUMMARY RULES\n"
            "Write 2-4 sentences. Describe what the candidate has actually spent their career doing, "
            "at what scale, and in what environment. Do not mirror or paraphrase the job spec's language.\n\n"
            "Do NOT use this structure: '[Title] with [credential phrase]. Expert in X. Skilled in Y.' "
            "It produces generic output every time.\n\n"
            "Do not use: proven track record, expert in, skilled in, adept, ensuring compliance, "
            "aligning outcomes with strategic objectives, robust governance, or any phrase lifted from the job spec.\n\n"
            "RIGHT: 'Programme manager with 15 years in financial services technology. Most recently ran the "
            "£20m Workspace 2.0 delivery at LSEG across 15 teams and 300k users. "
            "Comfortable with regulated environments, portfolio governance, and vendor negotiation.'\n\n"
            "WRONG: 'Senior Project Manager with a proven track record in governing technology portfolios "
            "within financial institutions. Expert in managing £20m+ budgets and ensuring compliance with "
            "project delivery frameworks.'\n\n"
            "### MANDATORY BULLET STRUCTURE RULE\n"
            "Every rewritten bullet point MUST strictly follow this exact structure:\n"
            "Verb of ownership → Scope → Strategic purpose → Quantified outcome\n"
            "Use only real metrics, budget scales, team sizes, or saving figures from the candidate's CV/database. Do NOT invent/hallucinate numbers.\n\n"
            "### COMPLETE COVERAGE REQUIREMENT\n"
            "You MUST review and rewrite relevant bullets for ALL historical roles listed on the CV (including LSEG, Bloomberg, UBS, and other past roles). Do not stop after the first/current role. Every past role must be tailored to align with the job description.\n\n"
            "### CLARITY & CONFIDENCE RULE\n"
            "Ensure recruiter clarity on: scope of responsibility, level of ownership, scale (team, budgets, platforms, users), governance, and impact. Make implicit details explicit only if supported by CV. Do not add filler/speculation.\n\n"
            "### OUTPUT FORMAT (CRITICAL FOR INLINE PATCHING)\n"
            "To surgically patch the .docx while preserving formatting, return proposed rewrites as updates. Every paragraph or bullet to align is a valid issue. Target the ENTIRE original paragraph to ensure clean replacement. Do NOT combine multiple separate bullets or paragraphs into a single update containing newlines (\\n). Each individual paragraph/bullet line must have its own separate issue block in the 'issues' array.\n\n"
            "Return response ONLY as a valid JSON object matching this structure:\n"
            "{\n"
            '  "strengths": ["List of CV strengths matching the job spec"],\n'
            '  "gaps": ["Detail where and why the CV could not match specific ATS keywords or job requirements (e.g., \'No evidence of regulatory reporting in LSEG role to match compliance requirement\', \'Lacks SAFe certification\')"],\n'
            '  "missing_keywords": ["Any target ATS keywords/technologies/domain terms missing from the candidate CV"],\n'
            '  "issues": [\n'
            '    {\n'
            '      "issue": "Description of why this bullet/paragraph needs alignment (e.g., lacks ATS keywords, needs seniority emphasis)",\n'
            '      "original_text": "Exact, word-for-word text from the current CV that you are rewriting",\n'
            '      "proposed_fix": "The completely rewritten, aligned, and repositioned bullet/paragraph",\n'
            '      "fixable": true\n'
            '    }\n'
            '  ],\n'
            '  "ats_match_pct": 75\n'
            "}\n"
            "Do NOT include any explanation, markdown code blocks, or text outside the JSON."
        )

        # Build a human-readable CV text from the structure for better LLM comprehension.
        cv_text_lines: list[str] = []
        current_section = "General"
        for elem in cv_structure:
            elem.get("style", "")
            is_heading = elem.get("is_heading", False)
            text = elem.get("text", "")
            if not text:
                continue
            # Clean text for section detection to avoid trailing space issues
            text_clean = text.strip()
            # Detect section headings (e.g., "Professional Experience:", "Education:")
            if is_heading or text_clean.endswith(":"):
                current_section = text_clean.rstrip(":")
            cv_text_lines.append(f"[{current_section}] {text}")
        cv_text = "\n".join(cv_text_lines)

        user_prompt = f"### JOB SPECIFICATION:\n{job_spec}\n\n### CURRENT CV CONTENT:\n{cv_text}\n\n"

        if cv_content_md.strip():
            user_prompt += (
                f"### CANDIDATE'S MODULAR CV REPOSITORY & ACHIEVEMENTS DATABASE (EXTRA CONTEXT):\n"
                f"Use the following modular repository as extra context, alternative summary options, and details to guide your tailoring. "
                f"It contains options (e.g. Option A, B, C for summaries) and role-specific bullet points. "
                f"Select and adapt the most relevant sections/achievements from this repository that match the job description, rather than treating this as a flat list of mandatory facts to include. "
                f"Do not invent facts outside of this repository and the current CV:\n{cv_content_md}\n\n"
            )



        user_prompt += (
            "### WARNING AGAINST HALLUCINATION:\n"
            "Do NOT invent any facts, project details, metrics, or technologies. "
            "If a keyword cannot be backed up by facts in the MODULAR CV REPOSITORY & ACHIEVEMENTS DATABASE or CURRENT CV CONTENT, simply do not mention it. "
            "Your output may infer reasonable responsibilities, skills and themes from evidence contained within the CV and modular repository.\n\n"
            "For example:\n"
            "- Budget ownership may support Budget Management.\n"
            "- Steering Committees may support Executive Stakeholder Management.\n"
            "- Governance activities may support Portfolio Governance.\n\n"
            "However, do not invent:\n"
            "- New projects\n"
            "- New technologies\n"
            "- New metrics\n"
            "- New budgets\n"
            "- New responsibilities\n"
            "- New stakeholder groups\n\n"
            "that are not supported by evidence.\n\n"
            "Failure to obey this constraint will make the CV invalid.\n\n"
            "Surgically rewrite and reposition the headline title, professional summary, Areas of Expertise, Career Highlights, and experience bullets in CURRENT CV CONTENT to align with the JOB SPECIFICATION. You MUST review and rewrite bullets across the entire CV (including all past employers like LSEG, Bloomberg, UBS, etc.); do not stop after the first role. Every single rewritten bullet point MUST strictly follow the structure: Verb of ownership → Scope → Strategic purpose → Quantified outcome. Use context from the achievements database.\n\n"
            "For every paragraph or bullet line you rewrite, you MUST specify the 'original_text' (the exact text of that single paragraph/bullet line in CURRENT CV CONTENT) and your rewritten 'proposed_fix'. Do NOT combine multiple bullets or paragraphs into a single update containing newlines (\\n); generate a separate issue block for each individual paragraph or bullet.\n\n"
            "Additionally, identify the candidate's target role/title line at the very top of the CV (e.g., 'Digital Delivery Manager | Digital Ecosystems...' or similar, typically the first line under their name) and propose a fix to align it with the job title and domain in the job spec (this MUST be included as a fix in your response)."
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
                client=self.client,
            )
        except Exception as e:
            logger.error(f"ERROR: LLM call failed: {e}")
            raise e

        # Try to extract JSON from markdown code blocks if present.
        json_match = re.search(r"```(?:json)?\s*(.*?)\s*```", raw_content, re.DOTALL)
        extracted = json_match.group(1).strip() if json_match else None

        data = None
        # Try direct parsing first (most reliable), then code-block extraction as fallback.
        for candidate in [raw_content.strip(), extracted]:
            try:
                data = json.loads(candidate or "")
                break
            except json.JSONDecodeError:
                continue

        parsed_data = {
            "strengths": [],
            "weaknesses": [],
            "gaps": [],
            "ats_match_pct": 0,
            "updates": [],
            "missing_keywords": []
        }
        if data is None:
            logger.error("LLM returned non-JSON content:\n%s", raw_content)
            if return_raw:
                return parsed_data, raw_content
            return parsed_data

        # Handle different possible structures returned by the model
        if isinstance(data, dict):
            parsed_data["strengths"] = [str(s).strip() for s in data.get("strengths", []) if str(s).strip()]
            parsed_data["gaps"] = [str(g).strip() for g in data.get("gaps", []) if str(g).strip()]
            parsed_data["missing_keywords"] = [str(k).strip() for k in data.get("missing_keywords", []) if str(k).strip()]
            try:
                parsed_data["ats_match_pct"] = int(data.get("ats_match_pct", 0))
            except (ValueError, TypeError):
                parsed_data["ats_match_pct"] = 0
            
            raw_issues = data.get("issues", [])
            if raw_issues and isinstance(raw_issues, list):
                updates = []
                weaknesses = []
                for item in raw_issues:
                    if not isinstance(item, dict):
                        continue
                    issue_text = item.get("issue", "").strip()
                    orig_text = item.get("original_text", "").strip()
                    proposed_fix = item.get("proposed_fix", "").strip()
                    is_unfixable = "cannot be improved without additional evidence" in proposed_fix.lower()
                    fixable = item.get("fixable", not is_unfixable)
                    
                    if not issue_text:
                        continue
                    
                    if fixable and proposed_fix and "cannot be improved without additional evidence" not in proposed_fix.lower():
                        updates.append({
                            "original_text": orig_text,
                            "new_text": proposed_fix
                        })
                        weaknesses.append(f"Fixed: {issue_text} (replaced '{orig_text}' with '{proposed_fix}')")
                    else:
                        weaknesses.append(f"Unresolved: {issue_text} (Cannot be improved without additional evidence)")
                
                parsed_data["updates"] = updates
                parsed_data["weaknesses"] = weaknesses
            else:
                # Fallback for compatibility
                raw_updates = data.get("updates", [])
                if isinstance(raw_updates, list):
                    parsed_data["updates"] = raw_updates
                    updates = raw_updates
                else:
                    parsed_data["updates"] = []
                    updates = []
                parsed_data["weaknesses"] = [str(w).strip() for w in data.get("weaknesses", []) if str(w).strip()]
        elif isinstance(data, list):
            updates = data
            parsed_data["updates"] = updates
        else:
            updates = []
            parsed_data["updates"] = updates

        # Auto‑insert job title if the LLM didn't include one
        title_keywords = ["manager", "lead", "director", "delivery", "programme", "project", "title"]
        target_title_para = None
        for idx, elem in enumerate(cv_structure):
            txt = elem.get("text", "")
            if idx > 0 and any(keyword in txt.lower() for keyword in title_keywords):
                target_title_para = txt
                break

        title_found = False
        if target_title_para:
            title_found = any(
                u.get("original_text", "").strip().lower() == target_title_para.strip().lower()
                for u in updates
            )

        if not title_found and target_title_para:
            match = re.search(r"(?i)job\s*title[:\s]+(.+)", job_spec)
            new_title = match.group(1).strip() if match else None
            if new_title:
                updates.append({"original_text": target_title_para, "new_text": new_title})

        # Strip section prefixes (e.g. [General] or **[General]**) and markdown bold from headings only.
        section_prefix_re = re.compile(r"^\[[^\]]+\]\s*")
        bold_section_prefix_re = re.compile(r"^\*\*\[[^\]]+\]\*\*\s*")
        heading_re = re.compile(r"^\*\*([^*]+)\*\*")
        for upd in updates:
            if "original_text" in upd:
                text = upd["original_text"].strip()
                text = bold_section_prefix_re.sub("", text)
                text = section_prefix_re.sub("", text)
                text = heading_re.sub(r"\1", text)
                upd["original_text"] = text
            if "new_text" in upd:
                text = upd["new_text"].strip()
                text = bold_section_prefix_re.sub("", text)
                text = section_prefix_re.sub("", text)
                text = heading_re.sub(r"\1", text)
                upd["new_text"] = text

        # Remove any update that targets generic headings (exact match after stripping leading whitespace).
        protected_headings = {"Career Highlights:", "Areas of Expertise:"}
        updates = [
            u
            for u in updates
            if not (
                u.get("original_text", "").strip() in protected_headings
                or u.get("new_text", "").strip() in protected_headings
            )
        ]

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

        parsed_data["updates"] = updates
        logger.info("LLM returned %d update(s): %s", len(updates), updates)

        if return_raw:
            return parsed_data, raw_content
        return parsed_data



    def generate_diff(self, job_spec: str, cv_structure: list[dict[str, Any]], cv_content_md: str) -> str:
        result = self.generate_tailored_content(job_spec, cv_structure, cv_content_md)
        updates = result.get("updates", [])
        if not updates:
            return "No changes detected."

        lines: list[str] = []
        for upd in updates:
            if isinstance(upd, dict):
                original = upd.get("original_text", "")
                new = upd.get("new_text", "")
                diff = difflib.unified_diff(
                    [original + "\n"],
                    [new + "\n"],
                    fromfile="src/cv_manager/data/CvContent.md",
                    tofile="src/cv_manager/data/CvContent.md",
                    lineterm="",
                )
                lines.extend(diff)
        return "\n".join(lines) if lines else "No changes detected."


if __name__ == "__main__":
    try:
        brain = CVBrain()
        test_updates = brain.generate_tailored_content(
            "Looking for a Python developer with experience in Streamlit.",
            [{"text": "I know Python", "style": "Normal"}],
            "I have built many web apps using Streamlit and FastAPI.",
        )
        print(test_updates)
    except Exception as e:
        print(f"Test failed: {e}")
