# Ensure the src directory is on PYTHONPATH so imports work when running via streamlit
import os, sys
# Add the repository root (two levels up from this file) to sys.path
repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if repo_root not in sys.path:
    sys.path.insert(0, repo_root)

# Ensure the src directory is on PYTHONPATH
src_path = os.path.join(repo_root, 'src')
if src_path not in sys.path:
    sys.path.insert(0, src_path)

# Removed unused import `text_area` and duplicate `os` import.
import streamlit as st
from cv_manager.parser.cv_parser import CVParser
from cv_manager.parser.cv_updater import CVUpdater
from cv_manager.brain import CVBrain
from docx import Document

# Configuration
CV_DIR = "cvs"
CV_CONTENT_PATH = "CVContent.md"

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
    return [f for f in os.listdir(CV_DIR) if f.endswith(".docx") and not f.startswith('~')]

def main():
    st.set_page_config(page_title="CV Manager", page_icon="📄", layout="wide")

    def main():
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
            st.markdown("Select a CV template and provide a job specification to begin the tailoring process.")
    st.markdown("Select a CV template and provide a job specification to begin the tailoring process.")

    # Sidebar for configuration/status
    with st.sidebar:
        st.header("Configuration")
        st.info(f"Scanning directory: `{CV_DIR}/`")
        
        cv_files = get_cv_files()
        if not cv_files:
            st.warning("No CV templates found in `cvs/`. Please add some `.docx` files.")
        else:
            st.success(f"Found {len(cv_files)} templates.")

    # Load template registry
    def load_registry():
        """Parse cvs_registry.md and return a dict mapping keyword to filename."""
        registry_path = os.path.join(os.getcwd(), 'cvs_registry.md')
        if not os.path.exists(registry_path):
            st.warning("Template registry not found.")
            return {}
        mapping = {}
        with open(registry_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        for line in lines:
            if line.strip().startswith('|') and '|' in line:
                parts = [p.strip() for p in line.split('|')[1:-1]]
                if len(parts) >= 2:
                    template_name, target = parts[0], parts[1]
                    mapping[target.lower()] = template_name
        return mapping

    registry_map = load_registry()

    # Two‑column layout: left for job spec & execution, right for output
    col_left, col_right = st.columns([4, 6])

    with col_left:
        st.subheader("1. Select Template")
        if cv_files:
            selected_cv = st.selectbox("Choose a CV to tailor:", cv_files)
            st.write(f"**Target File:** `{os.path.join(CV_DIR, selected_cv)}`")
        else:
            st.error("No templates available.")

    with col_left:
        st.subheader("2. Job Specification")
        job_spec = st.text_area(
            "Paste the job description here:",
            height=300,
            placeholder="Enter the requirements, responsibilities, and skills..."
        )

        # Load CV content from file
        cv_content = ""
        if os.path.exists(CV_CONTENT_PATH):
            with open(CV_CONTENT_PATH, "r", encoding="utf-8") as f:
                cv_content = f.read()
        else:
            st.warning(f"Note: `{CV_CONTENT_PATH}` not found. Proceeding without additional achievements.")

        # --- Keyword extraction & scoring ---------------------------------
        # Extract a set of candidate keywords from the job description
        job_keywords = {w.lower() for w in job_spec.split() if len(w) > 2}

        # Score each template by how many of those words appear in its text
        best_score = 0
        chosen_template = None
        for cv_file in cv_files:
            # Read the CV as plain text (or use parser to get structured data)
            txt = get_docx_text(os.path.join(CV_DIR, cv_file))
            score = sum(1 for kw in job_keywords if kw in txt.lower())
            if score > best_score:
                best_score = score
                chosen_template = cv_file

        if chosen_template and best_score > 0:
            st.info(f"Auto‑selected template `{chosen_template}` (score {best_score}).")
            selected_cv = chosen_template
        else:
            # Fallback to first available template
            if cv_files:
                selected_cv = cv_files[0]
                st.warning("No matching template found; defaulting to the first available template.")

        st.divider()

        # Action Section
        st.subheader("3. Execution")
        # Output will be shown in the right column
        with col_left:
            if st.button("🚀 Generate Tailored CV", type="primary", use_container_width=True):
                if not job_spec:
                    st.error("Please provide a job specification first.")
                elif not cv_files:
                    st.error("No CV templates found to work with.")
                else:
                    # Ensure diff_output is defined regardless of whether updates exist.
                    diff_output = ""
                    try:
                        with st.status("Tailoring in progress...", expanded=True) as status:
                            # 1. Parse the selected CV
                            st.write(f"🔍 Analyzing `{selected_cv}` structure...")
                            parser = CVParser(os.path.join(CV_DIR, selected_cv))
                            cv_structure = parser.parse()
                            
                            # 2. Generate updates using LLM
                            st.write("🧠 Consulting LLM for content alignment...")
                            brain = CVBrain()  # Assumes OPENAI_API_KEY is in env
                            updates = brain.generate_tailored_content(job_spec, cv_structure, cv_content)
                            
                            if not updates:
                                st.warning("The LLM didn't find any specific changes to make.")
                            else:
                                st.write(f"Found {len(updates)} potential updates.")
                                # 3. Apply updates
                                st.write("✍️ Applying surgical updates to document...")
                                updater = CVUpdater(os.path.join(CV_DIR, selected_cv))
                                base_name, ext = os.path.splitext(selected_cv)
                                # Increment an existing numeric suffix or add one if none exists.
                                import re
                                # Look for a trailing underscore followed by digits at the end of the name
                                pattern = r"_(\\d+)"
                                match = re.search(pattern, base_name)
                                if match:
                                    num = int(match.group(1)) + 1
                                    new_cv_name = f"{base_name.rsplit('_', 1)[0]}_{num}{ext}"
                                else:
                                    new_cv_name = f"{base_name}_1{ext}"
                                new_cv_path = os.path.join(CV_DIR, new_cv_name)
                                applied_count = 0
                                for update in updates:
                                    if updater.update_paragraph_text(update['original_text'], update['new_text']):
                                        applied_count += 1
                                updater.save(new_cv_path)
                                # Diff
                                import difflib
                                orig_text = get_docx_text(os.path.join(CV_DIR, selected_cv))
                                new_text = get_docx_text(new_cv_path)
                                diff_output = "\n".join(difflib.unified_diff(orig_text.splitlines(), new_text.splitlines(), fromfile=selected_cv, tofile=new_cv_name, lineterm=''))
                                st.success(
                                    f"Successfully applied {applied_count} updates! "
                                    f"New file: `{new_cv_name}`"
                                )
                                # Provide a direct download link for the updated CV.
                                with open(new_cv_path, "rb") as fp:
                                    data = fp.read()
                                st.download_button(
                                    label="Download Updated CV",
                                    data=data,
                                    file_name=new_cv_name,
                                    mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                                )
                            # Show diff in the right column
                            if diff_output:
                                with col_right:
                                    st.code(diff_output, language="diff")
                        status.update(label="Tailoring Complete!", state="complete", expanded=False)
                        st.balloons()
                    except Exception as e:
                        st.exception(e)
if __name__ == "__main__":
    main()
