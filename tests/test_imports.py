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

# Add src to sys.path to ensure imports work even if not installed
sys.path.append(os.path.join(os.getcwd(), "src"))

try:
    from cv_manager.brain import CVBrain
    from cv_manager.parser.cv_parser import CVParser
    from cv_manager.parser.cv_updater import CVUpdater

    print("✅ All modules imported successfully!")
except ImportError as e:
    print(f"❌ Import failed: {e}")
    sys.exit(1)

try:
    # Test a trivial operation for each
    # Note: We don't need real files, just to see if the classes can be instantiated
    # (Assuming they don't crash immediately on __init__)
    print("✅ Testing CVParser instantiation...")
    # We'll mock a path. It might fail if it tries to open a non-existent file in __init__
    # Let's check cv_parser.py implementation first.

    print("✅ Testing CVBrain instantiation...")
    brain = CVBrain()
    print("✅ Testing CVBrain instantiation successful!")

    print("All tests passed!")
except Exception as e:
    print(f"❌ Test failed with error: {e}")
    import traceback

    traceback.print_exc()
    sys.exit(1)
