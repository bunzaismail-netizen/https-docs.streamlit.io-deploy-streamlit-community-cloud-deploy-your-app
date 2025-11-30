import sys, os, time
ROOT = os.path.dirname(os.path.dirname(__file__))
SRC = os.path.join(ROOT, 'src')
if SRC not in sys.path:
    sys.path.insert(0, SRC)

from main import ClimateApp

app = ClimateApp()
# Simulate a login (bypass UI) using 'admin' to expose all pages
app.on_login('admin')

pages = ['home','dashboard','upload','visualization','prediction','report','about']
for p in pages:
    try:
        print('Showing', p)
        app.show_page(p)
        # process events briefly
        app.update()
        time.sleep(0.2)
    except Exception as e:
        print('Error showing', p, e)

print('Done')
# Clean up
try:
    app.destroy()
except Exception:
    pass
