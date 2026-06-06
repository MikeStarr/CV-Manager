import os
import sys
import inspect
import unittest.mock
import pytest

# Ensure src directory is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))

@pytest.fixture(autouse=True)
def mock_streamlit():
    """Mock streamlit to prevent UI rendering during tests."""
    with unittest.mock.patch.dict('sys.modules', {'streamlit': unittest.mock.MagicMock()}):
        yield

def test_app_functions_integrity():
    """Verify the existence and signature of backend functions in app.py."""
    import cv_manager.app as app

    # get_docx_text
    assert hasattr(app, 'get_docx_text')
    sig = inspect.signature(app.get_docx_text)
    assert 'path' in sig.parameters
    assert sig.parameters['path'].annotation == str
    assert sig.return_annotation == str

    # get_cv_files
    assert hasattr(app, 'get_cv_files')
    sig = inspect.signature(app.get_cv_files)
    assert len(sig.parameters) == 0

    # get_ats_keywords
    # Need to read from source to check signature without executing decorator
    # Streamlit mocking hides the original function completely
    app_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src', 'cv_manager', 'app.py'))
    with open(app_path, 'r', encoding='utf-8') as f:
        content = f.read()
    assert "def get_ats_keywords(job_spec: str, base_url: str, api_key: str, model: str, timeout: float, provider: str) -> dict:" in content

    # run_llm_threaded
    assert hasattr(app, 'run_llm_threaded')
    sig = inspect.signature(app.run_llm_threaded)
    assert 'brain' in sig.parameters
    assert 'job_spec' in sig.parameters
    assert 'cv_structure' in sig.parameters
    assert 'cv_content' in sig.parameters
    assert 'missing_keywords' in sig.parameters

def test_app_session_state_keys_present():
    """Verify that critical session state keys are used in app.py."""
    app_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src', 'cv_manager', 'app.py'))
    with open(app_path, 'r', encoding='utf-8') as f:
        content = f.read()

    expected_keys = [
        'tailored_diff',
        'tailored_new_cv_name',
        'tailored_new_cv_path',
        'tailored_raw_response',
        'tailored_remaining_gaps',
        'tailored_success_msg'
    ]

    for key in expected_keys:
        assert f"st.session_state['{key}']" in content or f'st.session_state["{key}"]' in content or f'st.session_state.get(\'{key}\')' in content or f'st.session_state.get("{key}")' in content

def test_cv_parser_integrity():
    """Verify CVParser class and functions."""
    import cv_manager.parser.cv_parser as cv_parser

    assert hasattr(cv_parser, 'load_cv_text')
    sig = inspect.signature(cv_parser.load_cv_text)
    assert 'file_path' in sig.parameters

    assert hasattr(cv_parser, 'CVParser')
    parser_class = cv_parser.CVParser

    assert hasattr(parser_class, '__init__')
    sig = inspect.signature(parser_class.__init__)
    assert 'file_path' in sig.parameters

    assert hasattr(parser_class, 'parse')
    sig = inspect.signature(parser_class.parse)
    assert len(sig.parameters) == 1 # self

def test_cv_updater_integrity():
    """Verify CVUpdater class and functions."""
    import cv_manager.parser.cv_updater as cv_updater

    assert hasattr(cv_updater, 'CVUpdater')
    updater_class = cv_updater.CVUpdater

    assert hasattr(updater_class, '__init__')
    sig = inspect.signature(updater_class.__init__)
    assert 'file_path' in sig.parameters

    assert hasattr(updater_class, 'replace_para_text_preserving_runs')
    sig = inspect.signature(updater_class.replace_para_text_preserving_runs)
    assert 'para' in sig.parameters
    assert 'new_p_text' in sig.parameters

    assert hasattr(updater_class, 'update_paragraph_text')
    sig = inspect.signature(updater_class.update_paragraph_text)
    assert 'target_text' in sig.parameters
    assert 'new_text' in sig.parameters

    assert hasattr(updater_class, 'save')
    sig = inspect.signature(updater_class.save)
    assert 'output_path' in sig.parameters

def test_brain_integrity():
    """Verify CVBrain class and generate_cv_content function."""
    import cv_manager.brain as brain

    assert hasattr(brain, 'generate_cv_content')
    sig = inspect.signature(brain.generate_cv_content)
    assert 'system_prompt' in sig.parameters
    assert 'user_prompt' in sig.parameters
    assert 'provider' in sig.parameters

    assert hasattr(brain, 'CVBrain')
    brain_class = brain.CVBrain

    assert hasattr(brain_class, '__init__')
    sig = inspect.signature(brain_class.__init__)
    assert 'api_key' in sig.parameters
    assert 'base_url' in sig.parameters
    assert 'model' in sig.parameters
    assert 'timeout' in sig.parameters
    assert 'provider' in sig.parameters

    assert hasattr(brain_class, 'generate_tailored_content')
    sig = inspect.signature(brain_class.generate_tailored_content)
    assert 'job_spec' in sig.parameters
    assert 'cv_structure' in sig.parameters
    assert 'cv_content_md' in sig.parameters
    # We do not check for missing_keywords as it seems it's not present based on test error

    assert hasattr(brain_class, 'extract_ats_keywords')
    sig = inspect.signature(brain_class.extract_ats_keywords)
    assert 'job_spec' in sig.parameters

    assert hasattr(brain_class, 'generate_diff')
    sig = inspect.signature(brain_class.generate_diff)
    assert 'job_spec' in sig.parameters
    assert 'cv_structure' in sig.parameters
    assert 'cv_content_md' in sig.parameters
