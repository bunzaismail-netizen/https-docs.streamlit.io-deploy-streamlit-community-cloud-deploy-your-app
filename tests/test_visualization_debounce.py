import sys
import time
import os
import tkinter as tk

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
SRC = os.path.join(ROOT, "src")
if SRC not in sys.path:
    sys.path.insert(0, SRC)
from visualization import VisualizationPage


def test_debounce_schedule_plot(tk_root):
    root = tk_root
    page = VisualizationPage(root)

    # monkeypatch plot with a simple counter
    counter = {"count": 0}

    def fake_plot():
        counter["count"] += 1

    page.plot = fake_plot

    # Rapidly call schedule_plot
    for _ in range(12):
        page.schedule_plot()
        time.sleep(0.02)

    # Process the event loop long enough for debounced call to run
    timeout = 2.0
    start = time.time()
    while time.time() - start < timeout:
        try:
            root.update()
        except Exception:
            pass
        if counter["count"] >= 1:
            time.sleep(0.35)
            try:
                root.update()
            except Exception:
                pass
            break
        time.sleep(0.01)

    # cleanup
    try:
        page.destroy()
    except Exception:
        pass

    assert counter["count"] == 1, f"Debounced plot should be called once, got {counter['count']}"
