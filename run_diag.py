import time
import threading

# Add project root to sys.path to allow imports when running as script
import sys, os
# Ensure src/ is on sys.path so imports like 'from login_page import ...' work
src_dir = os.path.join(os.path.abspath(os.path.dirname(__file__)), 'src')
sys.path.insert(0, src_dir)

from src.main import ClimateApp
from src.report_page import ReportPage

print('Creating app...')
app = ClimateApp()
print('Simulating login...')
# simulate a login
try:
    app.on_login('admin')
except Exception as e:
    print('on_login error:', e)

# Instantiate report page
print('Creating report page...')
report = app.pages.get('report')
if report is None:
    try:
        factory = app.page_factories.get('report')
        if callable(factory):
            report = factory()
            app.pages['report'] = report
        else:
            print('report factory not available')
            report = None
    except Exception as e:
        print('report factory error:', e)

# Call on_show to initialize canvas and possibly start background work
if report is not None and isinstance(report, ReportPage):
    try:
        report.on_show()
        print('report on_show called')
    except Exception as e:
        print('report on_show exception:', e)

# Start scheduler thread directly (avoid messagebox in start_schedule)
print('Starting scheduler thread...')
if report is not None and isinstance(report, ReportPage):
    try:
        report.sched_running = True
        sched_thread = threading.Thread(target=report.schedule_worker, args=(1,), daemon=True)
        sched_thread.start()
    except Exception as e:
        print('failed to start schedule thread:', e)

# Wait briefly to let thread run and then destroy the app to trigger the race
time.sleep(0.8)
print('Destroying app now...')
try:
    app.destroy()
except Exception as e:
    print('app.destroy exception:', e)

# Wait a moment to let background diagnostics print
time.sleep(1.0)
print('Script finished')
