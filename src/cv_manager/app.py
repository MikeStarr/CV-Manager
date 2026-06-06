# Ensure the src directory is on PYTHONPATH so imports work when running via streamlit
import os
import sys

# Add the repository root (two levels up from this file) to sys.path
repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if repo_root not in sys.path:
    sys.path.insert(0, repo_root)

# Ensure the src directory is on PYTHONPATH
src_path = os.path.join(repo_root, "src")
if src_path not in sys.path:
    sys.path.insert(0, src_path)

# Removed unused import `text_area` and duplicate `os` import.
import queue
import threading

import streamlit as st
from docx import Document
from dotenv import load_dotenv

from cv_manager.brain import CVBrain
from cv_manager.parser.cv_parser import CVParser
from cv_manager.parser.cv_updater import CVUpdater

# Load environment variables
load_dotenv()

# Configuration
CV_DIR = "cvs"
CV_CONTENT_PATH = os.path.join(os.path.dirname(__file__), "data", "CvContent.md")


# Helper to extract text from .docx files
def get_docx_text(path: str) -> str:
    """Return paragraph text from a .docx file, preserving *bold* and _italics_."""
    # ``parts`` collects the rendered paragraphs.  Explicitly typing it as
    # ``list[str]`` removes static‑analysis warnings about an unknown type.
    parts: list[str] = []
    for p in Document(path).paragraphs:
        # ``run_parts`` collects the formatted runs for a single paragraph.
        run_parts: list[str] = []
        for r in p.runs:
            txt = r.text
            if r.bold:
                txt = f"*{txt}*"
            if r.italic:
                txt = f"_{txt}_"
            run_parts.append(txt)
        parts.append("".join(run_parts))
    return "\n".join(parts)


def get_cv_files():
    """Return a list of .docx files in the cvs directory, ignoring temporary files."""
    if not os.path.exists(CV_DIR):
        os.makedirs(CV_DIR)
    return [f for f in os.listdir(CV_DIR) if f.endswith(".docx") and not f.startswith("~")]


# Cached function to extract ATS keywords to prevent redundant LLM calls
@st.cache_data(show_spinner="Running ATS Analysis on Job Specification...")
def get_ats_keywords(job_spec: str, base_url: str, api_key: str, model: str, timeout: float, provider: str) -> dict:
    brain = CVBrain(api_key=api_key or None, base_url=base_url, model=model, timeout=timeout, provider=provider)
    return brain.extract_ats_keywords(job_spec)


def run_llm_threaded(brain, job_spec, cv_structure, cv_content, missing_keywords):
    """Runs the LLM call in a background thread and returns the result or raises the exception."""
    res_queue = queue.Queue()

    def worker():
        try:
            res = brain.generate_tailored_content(
                job_spec, cv_structure, cv_content, return_raw=True, matched_keywords=missing_keywords
            )
            res_queue.put(("SUCCESS", res))
        except Exception as e:
            res_queue.put(("ERROR", e))

    t = threading.Thread(target=worker)
    t.start()
    return t, res_queue


def main():
    st.set_page_config(page_title="CV Manager", page_icon="📄", layout="wide")

    # Apple‑style container with subtle background
    st.markdown(
        """
        <style>
            .main {background-color:#f9fafb; padding-top:0px;}
            h1, h2, h3 {font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; margin-top:-20px;}
        </style>
        """,
        unsafe_allow_html=True,
    )

    container = st.container()
    with container:
        st.markdown("<h2 style='text-align:center;'>📄 CV Tailor Pro</h2>", unsafe_allow_html=True)
        st.markdown(
            "<p style='text-align:center;'>Analyze job specifications, identify keyword gaps, and surgically tailor your CV templates.</p>",
            unsafe_allow_html=True,
        )

    # Sidebar for configuration/status
    with st.sidebar:
        st.header("Configuration")
        st.info(f"Scanning directory: `{CV_DIR}/`")

        cv_files = get_cv_files()
        if not cv_files:
            st.warning("No CV templates found in `cvs/`. Please add some `.docx` files.")
        else:
            st.success(f"Found {len(cv_files)} templates.")

        st.divider()
        st.header("LLM Provider & Settings")

        llm_provider = st.selectbox("Select LLM Provider:", options=["Local", "DeepSeek", "Grok"], index=0)

        if llm_provider == "Local":
            # Read defaults from env
            default_base_url = os.getenv("OPENAI_BASE_URL") or "http://localhost:1234/v1"
            default_api_key = os.getenv("OPENAI_API_KEY") or ""
            default_model = os.getenv("LM_STUDIO_MODEL") or "llama-3.1-8b-instruct"
            default_timeout = int(os.getenv("OPENAI_TIMEOUT") or os.getenv("LLM_TIMEOUT") or "60")

            llm_base_url = st.text_input("API Base URL:", value=default_base_url)
            llm_api_key = st.text_input("API Key (optional):", value=default_api_key, type="password")
            llm_model = st.text_input("Model Name:", value=default_model)
            llm_timeout = st.number_input(
                "Timeout (seconds):", min_value=5, max_value=600, value=default_timeout, step=5
            )
        elif llm_provider == "DeepSeek":
            ds_key = os.getenv("DEEPSEEK_API_KEY")
            if ds_key:
                st.success("🔑 DeepSeek API Key loaded from environment.")
            else:
                st.error("⚠️ DeepSeek API Key missing! Set DEEPSEEK_API_KEY in your .env file.")

            llm_base_url = "https://api.deepseek.com"
            llm_api_key = ds_key or ""
            llm_model = "deepseek-chat"
            llm_timeout = st.number_input("Timeout (seconds):", min_value=5, max_value=600, value=15, step=5)
        elif llm_provider == "Grok":
            grok_key = os.getenv("XAI_API_KEY")
            if grok_key:
                st.success("🔑 Grok API Key loaded from environment.")
            else:
                st.error("⚠️ Grok API Key missing! Set XAI_API_KEY in your .env file.")

            llm_base_url = "https://api.x.ai/v1"
            llm_api_key = grok_key or ""
            llm_model = "grok-4.3"
            llm_timeout = st.number_input("Timeout (seconds):", min_value=5, max_value=600, value=15, step=5)

    # Two‑column layout: left for inputs and action, right for dashboards & outputs
    col_left, col_right = st.columns([4, 6])

    with col_left:
        st.subheader("1. Job Specification")
        job_spec = st.text_area(
            "Paste the job description here:",
            height=300,
            placeholder="Enter the requirements, responsibilities, and skills...",
        )

        # Load CV content from file
        cv_content = ""
        if os.path.exists(CV_CONTENT_PATH):
            with open(CV_CONTENT_PATH, encoding="utf-8") as f:
                cv_content = f.read()
        else:
            st.warning(f"Note: `{CV_CONTENT_PATH}` not found. Proceeding without additional achievements.")

    # Process ATS keywords and template scoring
    selected_cv = cv_files[0] if cv_files else None
    chosen_template = None
    ats_keywords = {"technical_skills": [], "soft_skills": [], "domain_and_certifications": []}
    flat_keywords = []
    template_scores = {}
    template_matches = {}

    ats_keywords_error = None
    if job_spec.strip():
        try:
            # Get ATS keywords (cached)
            ats_keywords = get_ats_keywords(job_spec, llm_base_url, llm_api_key, llm_model, llm_timeout, llm_provider)
            flat_keywords = (
                ats_keywords.get("technical_skills", [])
                + ats_keywords.get("soft_skills", [])
                + ats_keywords.get("domain_and_certifications", [])
            )
            flat_keywords = [k for k in flat_keywords if k.strip()]

            if flat_keywords:
                best_score = -1.0
                for cv_file in cv_files:
                    cv_path = os.path.join(CV_DIR, cv_file)
                    txt = get_docx_text(cv_path).lower()

                    matched = []
                    for kw in flat_keywords:
                        if kw.lower() in txt:
                            matched.append(kw)

                    score_pct = (len(matched) / len(flat_keywords)) * 100
                    template_scores[cv_file] = score_pct
                    template_matches[cv_file] = {
                        "matched": matched,
                        "missing": [k for k in flat_keywords if k not in matched],
                    }
                    if score_pct > best_score:
                        best_score = score_pct
                        chosen_template = cv_file

                if chosen_template:
                    selected_cv = chosen_template
        except Exception as e:
            ats_keywords_error = e

    with col_left:
        st.subheader("2. Selected Template")
        if cv_files:
            if chosen_template:
                st.info(f"🎯 **Best Match:** `{selected_cv}`")
            else:
                st.info(f"📂 **Default Template:** `{selected_cv}`")
        else:
            st.error("No templates available.")

        st.divider()

        # Action Section
        st.subheader("3. Execution")
        generate_clicked = st.button("🚀 Generate Tailored CV", type="primary", use_container_width=True)

        if generate_clicked:
            if not job_spec:
                st.error("Please provide a job specification first.")
            elif not cv_files:
                st.error("No CV templates found to work with.")
            else:
                assert selected_cv is not None
                # Clear previous session state on new generation
                st.session_state["tailored_raw_response"] = None
                st.session_state["tailored_diff"] = None
                st.session_state["tailored_new_cv_name"] = None
                st.session_state["tailored_new_cv_path"] = None
                st.session_state["tailored_success_msg"] = None
                st.session_state["tailored_remaining_gaps"] = None

                try:
                    with st.status("Tailoring in progress...", expanded=True) as status:
                        st.write(f"🔍 Analyzing `{selected_cv}` structure...")
                        parser = CVParser(os.path.join(CV_DIR, selected_cv))
                        cv_structure = parser.parse()

                        # Get missing keywords from ATS scan for the selected CV
                        missing_keywords = []
                        if selected_cv in template_matches:
                            missing_keywords = template_matches[selected_cv]["missing"]
                        else:
                            # Fallback if selected_cv isn't in matches
                            cv_text_lower = get_docx_text(os.path.join(CV_DIR, selected_cv)).lower()
                            missing_keywords = [k for k in flat_keywords if k.lower() not in cv_text_lower]

                        # Generate updates using LLM in a background thread
                        st.write("🧠 Consulting LLM for content alignment (background thread)...")
                        brain = CVBrain(
                            api_key=llm_api_key or None,
                            base_url=llm_base_url,
                            model=llm_model,
                            timeout=llm_timeout,
                            provider=llm_provider,
                        )

                        import time

                        thread, res_queue = run_llm_threaded(
                            brain, job_spec, cv_structure, cv_content, missing_keywords
                        )

                        # Monitor the thread in a non-blocking way
                        while thread.is_alive():
                            time.sleep(0.1)

                        # Retrieve the output or raise any exception encountered
                        status_type, result = res_queue.get()
                        if status_type == "ERROR":
                            raise result

                        if isinstance(result, tuple):
                            updates, raw_llm_response = result
                        else:
                            updates = result
                            raw_llm_response = None

                        if not updates:
                            st.warning("The LLM didn't find any specific changes to make.")
                            st.session_state["tailored_raw_response"] = raw_llm_response
                            st.session_state["tailored_diff"] = ""
                            st.session_state["tailored_new_cv_name"] = selected_cv
                            st.session_state["tailored_new_cv_path"] = os.path.join(CV_DIR, selected_cv)
                            st.session_state["tailored_success_msg"] = (
                                "The LLM analyzed the CV and did not suggest any updates."
                            )
                            if selected_cv in template_matches:
                                st.session_state["tailored_remaining_gaps"] = template_matches[selected_cv]["missing"]
                            else:
                                st.session_state["tailored_remaining_gaps"] = flat_keywords
                        else:
                            st.write(f"Found {len(updates)} potential updates.")
                            st.write("✍️ Applying surgical updates to document...")
                            updater = CVUpdater(os.path.join(CV_DIR, selected_cv))
                            base_name, ext = os.path.splitext(selected_cv)

                            # Increment an existing numeric suffix or add one if none exists.
                            import re

                            pattern = r"_(\d+)"
                            match = re.search(pattern, base_name)
                            if match:
                                num = int(match.group(1)) + 1
                                new_cv_name = f"{base_name.rsplit('_', 1)[0]}_{num}{ext}"
                            else:
                                new_cv_name = f"{base_name}_1{ext}"
                            new_cv_path = os.path.join(CV_DIR, new_cv_name)

                            applied_count = 0
                            for update in updates:
                                if updater.update_paragraph_text(update["original_text"], update["new_text"]):
                                    applied_count += 1
                            updater.save(new_cv_path)

                            # Diff
                            import difflib

                            orig_text = get_docx_text(os.path.join(CV_DIR, selected_cv))
                            new_text = get_docx_text(new_cv_path)
                            diff_output = "\n".join(
                                difflib.unified_diff(
                                    orig_text.splitlines(),
                                    new_text.splitlines(),
                                    fromfile=selected_cv,
                                    tofile=new_cv_name,
                                    lineterm="",
                                )
                            )

                            st.session_state["tailored_raw_response"] = raw_llm_response
                            st.session_state["tailored_diff"] = diff_output
                            st.session_state["tailored_new_cv_name"] = new_cv_name
                            st.session_state["tailored_new_cv_path"] = new_cv_path
                            st.session_state["tailored_success_msg"] = (
                                f"Successfully applied {applied_count} updates! New file: `{new_cv_name}`"
                            )

                            # Calculate remaining keyword gaps after tailoring
                            tailored_text = get_docx_text(new_cv_path).lower()
                            remaining_gaps = [k for k in flat_keywords if k.lower() not in tailored_text]
                            st.session_state["tailored_remaining_gaps"] = remaining_gaps

                    status.update(label="Tailoring Complete!", state="complete", expanded=False)
                    st.balloons()
                except Exception as e:
                    st.error(f"❌ **Tailoring Failed:** {e}")

    # Right Column Tabs Dashboard
    with col_right:
        tab_ats, tab_tailor = st.tabs(["📊 ATS Scan Dashboard", "📄 Tailored Output"])

        with tab_ats:
            if not job_spec.strip():
                st.info("Paste a job specification in the left column to run the ATS scan and analyze templates.")
            elif ats_keywords_error is not None:
                st.error(f"❌ **ATS Scan Error:** {ats_keywords_error}")
                st.info(
                    "Please verify your LLM settings (API Base URL, API Key, Model Name) in the sidebar configuration."
                )
            else:
                st.markdown("### 📊 ATS Analysis & Template Selection")

                # 1. Extracted Keywords categories
                st.write("#### 🔍 Extracted Keywords from Job Spec")
                k_col1, k_col2, k_col3 = st.columns(3)
                with k_col1:
                    st.markdown("**Technical Skills**")
                    tech_list = ats_keywords.get("technical_skills", [])
                    if tech_list:
                        for t in tech_list:
                            st.markdown(f"- `{t}`")
                    else:
                        st.write("*None extracted*")
                with k_col2:
                    st.markdown("**Soft Skills & Methodologies**")
                    soft_list = ats_keywords.get("soft_skills", [])
                    if soft_list:
                        for s in soft_list:
                            st.markdown(f"- `{s}`")
                    else:
                        st.write("*None extracted*")
                with k_col3:
                    st.markdown("**Domain & Certifications**")
                    domain_list = ats_keywords.get("domain_and_certifications", [])
                    if domain_list:
                        for d in domain_list:
                            st.markdown(f"- `{d}`")
                    else:
                        st.write("*None extracted*")

                st.write("---")

                # 2. CV Template Match Scores
                st.write("#### 📈 CV Template Match Rates")
                if template_scores:
                    # Sort templates by score
                    sorted_templates = sorted(template_scores.items(), key=lambda x: x[1], reverse=True)
                    for cv_file, score in sorted_templates:
                        is_selected = cv_file == selected_cv
                        label = f"**{cv_file}**" + (" *(Selected)*" if is_selected else "")
                        st.write(f"{label} — **{score:.1f}% Match**")
                        st.progress(score / 100.0)
                else:
                    st.write("*No scores available*")

                # 3. Selected CV Gap Analysis
                if selected_cv in template_matches:
                    st.write("---")
                    st.write(f"#### 🔍 Gap Analysis for Selected CV: `{selected_cv}`")
                    matches = template_matches[selected_cv]["matched"]
                    gaps = template_matches[selected_cv]["missing"]

                    col_m, col_g = st.columns(2)
                    with col_m:
                        st.success(f"✅ Matched Keywords ({len(matches)})")
                        if matches:
                            st.markdown(" ".join(f"`{m}`" for m in matches))
                        else:
                            st.write("None matched.")
                    with col_g:
                        st.warning(f"❌ Missing Keywords / Gaps ({len(gaps)})")
                        if gaps:
                            st.markdown(" ".join(f"`{g}`" for g in gaps))
                        else:
                            st.write("No gaps detected! Excellent template choice.")

        with tab_tailor:
            st.markdown("### 📄 Tailored CV Generation Output")
            if st.session_state.get("tailored_success_msg"):
                st.success(st.session_state["tailored_success_msg"])

                # Provide direct download button
                try:
                    with open(st.session_state["tailored_new_cv_path"], "rb") as fp:
                        data = fp.read()
                    st.download_button(
                        label="Download Updated CV",
                        data=data,
                        file_name=st.session_state["tailored_new_cv_name"],
                        mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                        use_container_width=True,
                    )
                except Exception as e:
                    st.error(f"Error loading tailored file for download: {e}")

                st.divider()

                col_l, col_r = st.columns(2)
                with col_l:
                    st.write("#### LLM Proposed Updates")
                    if st.session_state.get("tailored_raw_response"):
                        st.code(st.session_state["tailored_raw_response"], language="json")
                    else:
                        st.info("No raw response details.")
                with col_r:
                    st.write("#### Text Changes (Unified Diff)")
                    if st.session_state.get("tailored_diff"):
                        st.code(st.session_state["tailored_diff"], language="diff")
                    else:
                        st.info("No text changes detected.")

                # Display remaining keyword gaps
                st.divider()
                st.write("#### ⚠️ Remaining Keyword Gaps (Unmatched Requirements)")
                remaining_gaps = st.session_state.get("tailored_remaining_gaps", [])
                if remaining_gaps:
                    st.warning(
                        f"The tailored CV still lacks mentions of the following {len(remaining_gaps)} ATS keywords. You may need to address these manually or discuss them as transferable skills:"
                    )
                    st.markdown(" ".join(f"`{g}`" for g in remaining_gaps))
                else:
                    st.success(
                        "🎉 All ATS keywords have been successfully matched and incorporated into the tailored CV!"
                    )
            else:
                st.info("Click the **Generate Tailored CV** button in the left column to tailor the selected CV.")


if __name__ == "__main__":
    main()
