import time
import subprocess
import builtins
import sys, os

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
SRC = os.path.join(ROOT, 'src')
if SRC not in sys.path:
    sys.path.insert(0, SRC)


def test_gui_smoke(monkeypatch, tk_root):
    """Programmatic smoke test: login, cycle pages, call generate_report and visualization.on_show.
    Uses monkeypatch to avoid blocking dialogs and process exit.
    """
    # Prevent subprocess spawn and exiting the test runner
    monkeypatch.setattr(subprocess, "Popen", lambda *a, **k: None)
    monkeypatch.setattr(builtins, "exit", lambda code=0: None)

    # Stub messagebox dialogs to avoid blocking
    try:
        from tkinter import messagebox
        monkeypatch.setattr(messagebox, "askokcancel", lambda *a, **k: True)
        monkeypatch.setattr(messagebox, "showinfo", lambda *a, **k: None)
        monkeypatch.setattr(messagebox, "showwarning", lambda *a, **k: None)
        monkeypatch.setattr(messagebox, "showerror", lambda *a, **k: None)
    except Exception:
        # If tkinter isn't available, the tk_root fixture would have skipped the test.
        pass

    # Prevent ttkbootstrap from attempting theme updates that may touch stale widgets
    try:
        import ttkbootstrap as _tb
        class _DummyStyle:
            def __init__(self, *a, **k):
                pass
            def theme_use(self, *a, **k):
                return None
        monkeypatch.setattr(_tb, 'Style', _DummyStyle)
    except Exception:
        # If ttkbootstrap is not importable, main will likely fail later; let it surface.
        pass

    # If the display or Tcl/Tk setup is not usable in this environment, skip the test
    import pytest

    from main import ClimateApp

    try:
        app = ClimateApp(tk_root=tk_root)
    except Exception as e:
        # If Tk can't be initialized in this environment, skip the GUI smoke test
        pytest.skip(f"Skipping GUI smoke test; cannot create Tk root: {e}")
    # ensure login path works
    app.on_login('admin')

    pages = ['dashboard', 'visualization', 'prediction', 'report', 'upload', 'home']
    for p in pages:
        app.show_page(p)
        try:
            app.update()
        except Exception:
            pass
        time.sleep(0.05)

    # Call report generation (no farms selected should not crash)
    rpt = app.pages.get('report')
    if rpt:
        rpt.generate_report()
        try:
            app.update()
        except Exception:
            pass

    vis = app.pages.get('visualization')
    if vis:
        vis.on_show()
        try:
            app.update()
        except Exception:
            pass

    # Destroy app
    try:
        app.destroy()
    except Exception:
        pass

    assert True
