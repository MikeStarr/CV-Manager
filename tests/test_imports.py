import os
import sys
import importlib.util

# Ensure src directory is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))

def test_app_import():
    """Verify that app.py can be imported without syntax or dependency errors."""
    spec = importlib.util.spec_from_file_location("app", os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src', 'cv_manager', 'app.py')))
    module = importlib.util.module_from_spec(spec)
    # Mock streamlit before executing module
    import unittest.mock
    with unittest.mock.patch.dict('sys.modules', {'streamlit': unittest.mock.MagicMock()}):
        spec.loader.exec_module(module)
    assert module is not None
    
def test_other_imports():
    """Verify that other modules can be imported without syntax or dependency errors."""
    import cv_manager.brain
    import cv_manager.parser.cv_parser
    import cv_manager.parser.cv_updater
    assert cv_manager.brain is not None
    assert cv_manager.parser.cv_parser is not None
    assert cv_manager.parser.cv_updater is not None
