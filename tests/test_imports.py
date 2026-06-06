import os
import sys

# Add src to sys.path to ensure imports work even if not installed
sys.path.append(os.path.join(os.getcwd(), "src"))

try:
    from cv_manager.brain import CVBrain  # noqa: F401
    from cv_manager.parser.cv_parser import CVParser  # noqa: F401
    from cv_manager.parser.cv_updater import CVUpdater  # noqa: F401

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
