import sys, os, time
import subprocess
import builtins

ROOT = os.path.dirname(os.path.dirname(__file__))
SRC = os.path.join(ROOT, 'src')
if SRC not in sys.path:
    sys.path.insert(0, SRC)

def test_logout_no_exit(monkeypatch):
    """Run a logout flow but prevent the process from actually exiting during tests."""
    # Prevent spawning a subprocess and exiting the test runner
    monkeypatch.setattr(subprocess, "Popen", lambda *a, **k: None)
    monkeypatch.setattr(builtins, "exit", lambda code=0: None)

    # Silence any blocking messagebox dialogs used in logout
    try:
        from tkinter import messagebox
        monkeypatch.setattr(messagebox, "askokcancel", lambda *a, **k: True)
        monkeypatch.setattr(messagebox, "showinfo", lambda *a, **k: None)
        monkeypatch.setattr(messagebox, "showwarning", lambda *a, **k: None)
        monkeypatch.setattr(messagebox, "showerror", lambda *a, **k: None)
    except Exception:
        # If tkinter isn't available in headless test env, skip messagebox patching
        pass

    from main import ClimateApp

    app = ClimateApp()
    app.on_login('admin')
    # show several pages
    for p in ['dashboard', 'visualization', 'prediction', 'report', 'upload', 'home']:
        try:
            app.show_page(p)
            app.update()
            time.sleep(0.05)
        except Exception as e:
            print('show_page error', p, e)
    # simulate logout
    print('Calling logout()')
    app.logout()
    print('Logout called')
    # If the app still exists, attempt to destroy it; ensure we didn't exit the test runner
    try:
        if getattr(app, 'winfo_exists', lambda: False)():
            app.destroy()
    except Exception:
        pass
