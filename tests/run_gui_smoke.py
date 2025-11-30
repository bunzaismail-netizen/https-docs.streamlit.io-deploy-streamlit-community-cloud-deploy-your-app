import sys, os, time

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
SRC = os.path.join(ROOT, 'src')
if SRC not in sys.path:
    sys.path.insert(0, SRC)

# Patch messagebox to avoid blocking dialogs during automated smoke run
try:
    import tkinter as tk
    from tkinter import messagebox
    messagebox.askokcancel = lambda *a, **k: True
    messagebox.showinfo = lambda *a, **k: print('[messagebox.showinfo]', a)
    messagebox.showwarning = lambda *a, **k: print('[messagebox.showwarning]', a)
    messagebox.showerror = lambda *a, **k: print('[messagebox.showerror]', a)
except Exception:
    pass

from main import ClimateApp

print('Starting GUI smoke script')
app = ClimateApp()
print('Created ClimateApp')
# simulate login
try:
    app.on_login('admin')
    print('Logged in as admin')
except Exception as e:
    print('on_login error:', e)

pages = ['dashboard', 'visualization', 'prediction', 'report', 'upload', 'home']
for p in pages:
    try:
        print('Showing page', p)
        app.show_page(p)
        # process pending events
        try:
            app.update()
        except Exception:
            pass
        time.sleep(0.2)
    except Exception as e:
        print('show_page error', p, e)

# call report generate (should warn about no farms selected but not crash)
try:
    rpt = app.pages.get('report')
    if rpt:
        print('Calling generate_report()')
        rpt.generate_report()
        try:
            app.update()
        except Exception:
            pass
        time.sleep(0.2)
except Exception as e:
    print('generate_report error:', e)

# visualization on_show
try:
    vis = app.pages.get('visualization')
    if vis:
        print('Calling visualization.on_show()')
        vis.on_show()
        try:
            app.update()
        except Exception:
            pass
        time.sleep(0.2)
except Exception as e:
    print('visualization error:', e)

print('Destroying app')
try:
    app.destroy()
except Exception as e:
    print('destroy error:', e)
print('Smoke script finished')
