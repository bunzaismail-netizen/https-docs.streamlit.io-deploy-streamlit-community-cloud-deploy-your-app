import pandas as pd
from db_handler import DBHandler
import os

def import_file_to_db(file_path, farm_id=None):
    """
    Import data from a CSV or Excel file into climate_data and agri_metrics tables.
    If farm_id is provided, it will be used for all rows (otherwise must be in file).
    """
    if not os.path.isfile(file_path):
        raise FileNotFoundError(f"File not found: {file_path}")
    ext = os.path.splitext(file_path)[1].lower()
    if ext in ['.csv']:
        df = pd.read_csv(file_path)
    elif ext in ['.xls', '.xlsx']:
        df = pd.read_excel(file_path)
    else:
        raise ValueError("Unsupported file type. Only CSV and Excel are supported.")

    # Normalize column names
    df.columns = [c.strip().lower() for c in df.columns]

    # Required columns for each table
    climate_cols = ['date', 'temp_max', 'temp_min', 'rainfall']
    agri_cols = ['date', 'daily_gdd', 'effective_rainfall', 'cumulative_gdd']

    inserted = 0
    with DBHandler() as db:
        for _, row in df.iterrows():
            # Use provided farm_id or from file
            fid = farm_id or row.get('farm_id')
            if not fid:
                continue  # skip if no farm_id
            # Insert into climate_data
            if all(col in row for col in climate_cols):
                db.execute_query(
                    "INSERT OR REPLACE INTO climate_data (farm_id, date, temp_max, temp_min, rainfall) VALUES (?, ?, ?, ?, ?)",
                    (fid, row['date'], row['temp_max'], row['temp_min'], row['rainfall'])
                )
            # Insert into agri_metrics
            if all(col in row for col in agri_cols):
                db.execute_query(
                    "INSERT OR REPLACE INTO agri_metrics (farm_id, date, daily_gdd, effective_rainfall, cumulative_gdd) VALUES (?, ?, ?, ?, ?)",
                    (fid, row['date'], row['daily_gdd'], row['effective_rainfall'], row['cumulative_gdd'])
                )
            inserted += 1
    return inserted
