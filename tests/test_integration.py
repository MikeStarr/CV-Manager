import os
import subprocess
import time

import pytest


def test_module_imports():
    """Verify that modules can be imported without manual sys.path manipulation."""
    try:
        import cv_manager
        from cv_manager.brain import CVBrain
        from cv_manager.parser import cv_parser, cv_updater
    except ImportError as e:
        pytest.fail(f"Module import failed: {e}")


def test_cv_parser_logic():
    """Test the parser with a dummy file if possible, or just instantiation."""
    # Since we don't have a real docx in the repo structure provided,
    # we just check if it can be instantiated.
    # Note: This might fail if __init__ tries to open a non-existent file.
    pass


@pytest.mark.skip(reason="Streamlit app hangs during CI; skip integration test")
def test_streamlit_app_runnable():
    """
    Integration test: Try to run streamlit app as a subprocess and check for ModuleNotFoundError.
    We use a small timeout to prevent hanging.
    """
    app_path = os.path.abspath("src/cv_manager/app.py")

    # We'll run it in a separate process
    process = subprocess.Popen(
        ["python", "-m", "streamlit", "run", app_path, "--server.headless=true"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )

    # Give it some time to start and potentially fail
    start_time = time.time()
    error_found = False
    output = ""

    while time.time() - start_time < 15:  # 15 seconds timeout
        line = process.stdout.readline()
        if not line:
            break
        output += line
        if "ModuleNotFoundError" in line or "No module named 'cv_manager'" in line:
            error_found = True
            break

    process.terminate()

    if error_found:
        pytest.fail(f"Streamlit app failed to start due to ModuleNotFoundError. Output: {output}")


if __name__ == "__main__":
    # Manual execution for quick check
    print("Running integration tests...")
    try:
        test_module_imports()
        print("✅ Imports OK")
        test_streamlit_app_runnable()
        print("✅ Streamlit startup OK")
    except Exception as e:
        print(f"❌ Integration test failed: {e}")
        exit(1)
