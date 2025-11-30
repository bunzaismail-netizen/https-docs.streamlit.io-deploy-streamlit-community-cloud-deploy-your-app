import os
import sys
import time
# ensure src is importable
ROOT = os.path.dirname(os.path.dirname(__file__))
SRC = os.path.join(ROOT, 'src')
if SRC not in sys.path:
    sys.path.insert(0, SRC)

import tkinter as tk
from db_handler import DBHandler
from visualization import VisualizationPage

OUT_PNG = os.path.join(os.path.dirname(__file__), 'visualization_sample.png')

# create sample data in the real DB (src/climate.db)
with DBHandler() as db:
    # create test farm
    db.execute_query("INSERT OR IGNORE INTO farms (name, location, base_temp) VALUES (?, ?, ?)", ("Sample Farm", "Testville", 10.0))
    farm = db.fetch_one("SELECT id FROM farms WHERE name=?", ("Sample Farm",))
    if not farm:
        raise RuntimeError("Failed to create/find farm")
    farm_id = farm[0]
    # purge any old sample rows (by date range)
    db.execute_query("DELETE FROM climate_data WHERE farm_id=? AND date LIKE '2099-%'", (farm_id,))
    db.execute_query("DELETE FROM agri_metrics WHERE farm_id=? AND date LIKE '2099-%'", (farm_id,))
    rows = [
        (farm_id, '2099-01-01', 25.0, 15.0, 0.0),
        (farm_id, '2099-01-02', 26.5, 16.0, 2.0),
        (farm_id, '2099-01-03', 24.0, 14.5, 5.0),
        (farm_id, '2099-01-04', 27.0, 17.0, 0.0),
    ]
    for r in rows:
        db.execute_query("INSERT INTO climate_data (farm_id, date, temp_max, temp_min, rainfall) VALUES (?, ?, ?, ?, ?)", r)
    metrics = [
        (farm_id, '2099-01-01', 5.0, 0.0, 100.0),
        (farm_id, '2099-01-02', 6.0, 1.0, 106.0),
        (farm_id, '2099-01-03', 4.0, 2.0, 110.0),
        (farm_id, '2099-01-04', 7.0, 0.0, 117.0),
    ]
    for m in metrics:
        db.execute_query("INSERT INTO agri_metrics (farm_id, date, daily_gdd, effective_rainfall, cumulative_gdd) VALUES (?, ?, ?, ?, ?)", m)

# instantiate a hidden Tk root and the VisualizationPage
root = tk.Tk()
root.withdraw()
page = VisualizationPage(root)
# set the farm selection
page.load_farms()
page.farm_ids = getattr(page, 'farm_ids', [farm_id])
page.selected_farm_id = farm_id
# ensure on_show and plot
page.on_show()
# small wait to allow safe_ui_update scheduling if used
time.sleep(0.1)
page.plot()
# give it a moment
root.update_idletasks()
time.sleep(0.1)
# save the figure if present
fig = getattr(page, 'fig', None)
if fig is not None:
    try:
        fig.savefig(OUT_PNG)
        print(f"Saved sample plot to: {OUT_PNG}")
    except Exception as e:
        print("Failed to save figure:", e)
else:
    print("No figure available on page (fig is None)")

# cleanup Tk
try:
    page.destroy()
except Exception:
    pass
root.destroy()
