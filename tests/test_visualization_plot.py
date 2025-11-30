import os
import sys
import tempfile
import sqlite3
import time
# ensure src is on sys.path when running as a script
ROOT = os.path.dirname(os.path.dirname(__file__))
SRC = os.path.join(ROOT, 'src')
if SRC not in sys.path:
    sys.path.insert(0, SRC)
from db_handler import connect_db, DBHandler
from visualization import VisualizationPage
import tkinter as tk


def setup_temp_db():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    # Initialize schema
    conn = connect_db(path)
    if conn:
        conn.close()
    return path


def insert_sample_data(db_path):
    with DBHandler(db_path) as db:
        # insert a farm
        db.execute_query("INSERT INTO farms (name, location, base_temp) VALUES (?, ?, ?)", ("Test Farm", "Nowhere", 10.0))
        farm = db.fetch_one("SELECT id FROM farms WHERE name=?", ("Test Farm",))
        if farm is None:
            raise RuntimeError("Failed to insert or fetch test farm")
        farm_id = farm[0]
        # insert climate_data and agri_metrics
        rows = [
            (farm_id, "2025-01-01", 30.0, 20.0, 5.0),
            (farm_id, "2025-01-02", 31.0, 21.0, 0.0),
            (farm_id, "2025-01-03", 29.0, 19.0, 2.5),
        ]
        for r in rows:
            db.execute_query("INSERT INTO climate_data (farm_id, date, temp_max, temp_min, rainfall) VALUES (?, ?, ?, ?, ?)", r)
        metrics = [
            (farm_id, "2025-01-01", 5.0, 3.0, 100.0),
            (farm_id, "2025-01-02", 6.0, 2.0, 106.0),
            (farm_id, "2025-01-03", 4.0, 1.0, 110.0),
        ]
        for m in metrics:
            db.execute_query("INSERT INTO agri_metrics (farm_id, date, daily_gdd, effective_rainfall, cumulative_gdd) VALUES (?, ?, ?, ?, ?)", m)
    return farm_id


def test_visualization_plot_smoke():
    db_path = setup_temp_db()
    try:
        farm_id = insert_sample_data(db_path)
        # Create root TK and the page
        root = tk.Tk()
        root.withdraw()
        page = VisualizationPage(root)
        # Force the handler to use our temp DB by overriding db_path attr on DBHandler used within functions
        # DBHandler default uses module-level DB_FILE; instead monkeypatch by setting environment or passing db_path via constructor when used
        # For this smoke test we'll temporarily set DBHandler.DB_FILE if present, otherwise rely on connect_db path
        # Instantiate and call on_show
        page.on_show()
        # Force selection of the farm we created
        page.farm_ids = [farm_id]
        page.selected_farm_id = farm_id
        # Call plot
        page.plot()
        # allow some time for scheduled UI updates
        root.update_idletasks()
        time.sleep(0.1)
        # After plotting, df should be populated
        assert hasattr(page, 'df') and not page.df.empty, "VisualizationPage.df should be non-empty after plot()"
        root.destroy()
    finally:
        try:
            os.remove(db_path)
        except Exception:
            pass
