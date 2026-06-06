# Ensure the src directory is on PYTHONPATH so imports work when running via streamlit
# ruff: noqa: E402
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


def run_llm_threaded(brain, job_spec, cv_structure, cv_content):
    """Runs the LLM call in a background thread and returns the result or raises the exception."""
    res_queue = queue.Queue()

    def worker():
        try:
            res = brain.generate_tailored_content(
                job_spec, cv_structure, cv_content, return_raw=True
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

        llm_provider = st.selectbox("Select LLM Provider:", options=["Local", "ChatGPT", "DeepSeek", "Grok"], index=0)

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
        elif llm_provider == "ChatGPT":
            openai_key = os.getenv("OPENAI_API_KEY")
            if openai_key:
                st.success("🔑 OpenAI API Key loaded from environment.")
            else:
                st.error("⚠️ OpenAI API Key missing! Set OPENAI_API_KEY in your .env file.")

            llm_base_url = "https://api.openai.com/v1"
            llm_api_key = openai_key or ""
            llm_model = "gpt-4o"
            llm_timeout = st.number_input("Timeout (seconds):", min_value=5, max_value=600, value=15, step=5)
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

    # Template selection
    with col_left:
        st.subheader("2. Select CV Template")
        if cv_files:
            selected_cv = st.selectbox(
                "Choose a template CV to audit and tailor:",
                options=cv_files,
                index=0,
            )
        else:
            selected_cv = None
            st.error("No templates available in `cvs/`. Please add some `.docx` files.")

        st.divider()

        # Action Section
        st.subheader("3. Execution")
        generate_clicked = st.button("🚀 Generate Tailored CV", type="primary", use_container_width=True)

        if generate_clicked:
            if not job_spec:
                st.error("Please provide a job specification first.")
            elif not cv_files or not selected_cv:
                st.error("No CV template selected or available to work with.")
            else:
                # Clear previous session state on new generation
                st.session_state["tailored_raw_response"] = None
                st.session_state["tailored_diff"] = None
                st.session_state["tailored_new_cv_name"] = None
                st.session_state["tailored_new_cv_path"] = None
                st.session_state["tailored_success_msg"] = None
                st.session_state["tailored_strengths"] = []
                st.session_state["tailored_weaknesses"] = []
                st.session_state["tailored_ats_match_pct"] = 0
                st.session_state["tailored_missing_keywords"] = []
                st.session_state["tailored_gaps"] = []

                try:
                    with st.status("Tailoring in progress...", expanded=True) as status:
                        st.write(f"🔍 Analyzing `{selected_cv}` structure...")
                        parser = CVParser(os.path.join(CV_DIR, selected_cv))
                        cv_structure = parser.parse()

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
                            brain, job_spec, cv_structure, cv_content
                        )

                        # Monitor the thread in a non-blocking way
                        while thread.is_alive():
                            time.sleep(0.1)

                        # Retrieve the output or raise any exception encountered
                        status_type, result = res_queue.get()
                        if status_type == "ERROR":
                            raise result

                        if isinstance(result, tuple):
                            audit_data, raw_llm_response = result
                        else:
                            audit_data = result
                            raw_llm_response = None

                        updates = audit_data.get("updates", [])
                        strengths = audit_data.get("strengths", [])
                        weaknesses = audit_data.get("weaknesses", [])
                        ats_match_pct = audit_data.get("ats_match_pct", 0)

                        st.session_state["tailored_strengths"] = strengths
                        st.session_state["tailored_weaknesses"] = weaknesses
                        st.session_state["tailored_ats_match_pct"] = ats_match_pct
                        st.session_state["tailored_missing_keywords"] = audit_data.get("missing_keywords", [])
                        st.session_state["tailored_gaps"] = audit_data.get("gaps", [])

                        if not updates:
                            st.warning("The LLM didn't find any specific changes to make.")
                            st.session_state["tailored_raw_response"] = raw_llm_response
                            st.session_state["tailored_diff"] = ""
                            st.session_state["tailored_new_cv_name"] = selected_cv
                            st.session_state["tailored_new_cv_path"] = os.path.join(CV_DIR, selected_cv)
                            st.session_state["tailored_success_msg"] = (
                                "The LLM analyzed the CV and did not suggest any updates."
                            )
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

                    status.update(label="Tailoring Complete!", state="complete", expanded=False)
                    st.balloons()
                except Exception as e:
                    st.error(f"❌ **Tailoring Failed:** {e}")

    # Right Column: Unified CV Audit & Tailoring Output
    with col_right:
        st.markdown("### 📄 CV Audit & Tailoring Output")
        if st.session_state.get("tailored_success_msg"):
            st.success(st.session_state["tailored_success_msg"])

            # Render missing keywords if any
            missing_keywords = st.session_state.get("tailored_missing_keywords", [])
            if missing_keywords:
                st.warning(f"⚠️ **Missing Target ATS Keywords:** {', '.join(missing_keywords)}")

            # Audit Results Row
            aud_col1, aud_col2, aud_col3 = st.columns([3, 4, 4])
            with aud_col1:
                match_pct = st.session_state.get("tailored_ats_match_pct", 0)
                st.metric("ATS Match Rate", f"{match_pct}%")
            with aud_col2:
                with st.expander("✅ CV Strengths", expanded=True):
                    strengths = st.session_state.get("tailored_strengths", [])
                    if strengths:
                        for s in strengths:
                            st.markdown(f"- {s}")
                    else:
                        st.write("*No strengths documented*")
            with aud_col3:
                with st.expander("⚠️ CV Gaps & Weaknesses", expanded=True):
                    gaps = st.session_state.get("tailored_gaps", [])
                    unresolved = [w for w in st.session_state.get("tailored_weaknesses", []) if w.startswith("Unresolved:")]
                    
                    if gaps or unresolved:
                        for g in gaps:
                            st.markdown(f"- {g}")
                        for u in unresolved:
                            clean_u = u.replace("Unresolved:", "").strip()
                            st.markdown(f"- **Unresolved Item:** {clean_u}")
                    else:
                        st.write("*No gaps or weaknesses documented*")

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
        else:
            st.info("Click the **Generate Tailored CV** button in the left column to tailor the selected CV.")


if __name__ == "__main__":
    main()
