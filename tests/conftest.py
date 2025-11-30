import pytest
import sys
import os
import tkinter as tk

# Ensure src is importable
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
SRC = os.path.join(ROOT, "src")
if SRC not in sys.path:
    sys.path.insert(0, SRC)


@pytest.fixture(scope="session")
def tk_root():
    """Create a hidden Tk root for tests that need the Tk event loop."""
    try:
        # Some headless environments may not have a working Tcl/Tk installation.
        # Attempt to create a root; if that fails, skip Tk-dependent tests.
        root = tk.Tk()
        root.withdraw()
    except Exception as e:
        pytest.skip(f"Tk root unavailable: {e}")
        return
    yield root
    try:
        root.update()
    except Exception:
        pass
    try:
        root.destroy()
    except Exception:
        pass
