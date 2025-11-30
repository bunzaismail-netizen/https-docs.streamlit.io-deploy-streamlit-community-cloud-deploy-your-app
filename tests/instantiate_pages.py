import sys
import os
import tkinter as tk
import traceback

# Ensure the src directory is on sys.path so we can import modules
ROOT = os.path.dirname(os.path.dirname(__file__))
SRC = os.path.join(ROOT, 'src')
if SRC not in sys.path:
    sys.path.insert(0, SRC)

PAGES = [
    ("home_about", "HomePage"),
    ("dashboard", "Dashboard"),
    ("upload_page", "UploadPage"),
    ("visualization", "VisualizationPage"),
    ("prediction", "PredictionPage"),
    ("report_page", "ReportPage"),
]

root = tk.Tk()
root.withdraw()

results = {}
for module_name, class_name in PAGES:
    try:
        mod = __import__(module_name)
        cls = getattr(mod, class_name)
        print(f"Instantiating {class_name} from {module_name}...")
        obj = cls(root)
        if hasattr(obj, 'on_show'):
            try:
                obj.on_show()
            except Exception as e:
                print(f"on_show of {class_name} raised: {e}")
        try:
            obj.destroy()
        except Exception:
            pass
        results[module_name] = 'OK'
        print(f"{module_name}: OK")
    except Exception as e:
        print(f"{module_name}: FAILED")
        traceback.print_exc()
        results[module_name] = f'FAILED: {e}'

print('\nSummary:')
for k, v in results.items():
    print(k, v)

root.destroy()
