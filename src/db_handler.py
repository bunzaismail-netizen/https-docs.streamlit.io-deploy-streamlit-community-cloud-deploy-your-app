"""
db_handler.py
Module for database handling functions and classes, including advanced utility methods
for summary statistics, data import/export, and easier integration with dashboards.
"""

import sqlite3
import os
from typing import Optional, List, Tuple, Any, Dict, Union
import csv

# Default database path (project root by default)
DB_FILE = os.path.join(os.path.dirname(__file__), "climate.db")


def connect_db(db_path: str = DB_FILE) -> Optional[sqlite3.Connection]:
    """
    Connect to the SQLite database (default: climate.db in project root).
    Ensures required tables exist.
    Returns:
        sqlite3.Connection or None
    """
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        # Migration: only attempt to alter users table if it already exists.
        cursor.execute("PRAGMA table_info(users)")
        columns = [row[1] for row in cursor.fetchall()]
        if columns:
            # users table exists; ensure 'status' column is present
            if "status" not in columns:
                try:
                    cursor.execute("ALTER TABLE users ADD COLUMN status TEXT DEFAULT 'active'")
                except sqlite3.Error:
                    # If migration fails for any reason, continue and recreate expected tables below
                    pass

        # Create required tables if they don't exist
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS farms (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE,
                location TEXT,
                base_temp REAL
            )
            """
        )
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS climate_data (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                farm_id INTEGER,
                date TEXT,
                temp_max REAL,
                temp_min REAL,
                rainfall REAL,
                FOREIGN KEY(farm_id) REFERENCES farms(id)
            )
            """
        )
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS agri_metrics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                farm_id INTEGER,
                date TEXT,
                daily_gdd REAL,
                effective_rainfall REAL,
                cumulative_gdd REAL,
                FOREIGN KEY(farm_id) REFERENCES farms(id)
            )
            """
        )
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                role TEXT DEFAULT 'user',
                status TEXT DEFAULT 'active'
            )
            """
        )
        conn.commit()
        return conn
    except sqlite3.Error as e:
        print(f"❌ Database connection failed: {e}")
        return None


class DBHandler:
    def detect_season(self, date_str: str) -> str:
        """
        Detect season from a date string (YYYY-MM-DD). Default logic:
        - Dec/Jan/Feb: Winter
        - Mar/Apr/May: Spring
        - Jun/Jul/Aug: Summer
        - Sep/Oct/Nov: Fall
        Returns: season name as string
        """
        import datetime
        try:
            month = int(date_str.split("-")[1])
        except Exception:
            return "Unknown"
        if month in [12, 1, 2]:
            return "Winter"
        elif month in [3, 4, 5]:
            return "Spring"
        elif month in [6, 7, 8]:
            return "Summer"
        elif month in [9, 10, 11]:
            return "Fall"
        return "Unknown"

    def log_audit(self, action: str, details: str):
        """Append an audit log entry to user_audit_log.csv."""
        import csv, datetime, os
        log_file = os.path.join(os.path.dirname(__file__), "..", "user_audit_log.csv")
        with open(log_file, "a", newline="") as f:
            writer = csv.writer(f)
            writer.writerow([datetime.datetime.now().isoformat(), action, details])
    # Duplicate get_users method removed to resolve method declaration conflict.
    def set_user_status(self, user_id: int, status: str) -> None:
        """Set user status to 'active' or 'inactive'."""
        self.execute_query("UPDATE users SET status=? WHERE id=?", (status, user_id))

    def get_all_users(self) -> List[Dict[str, Any]]:
        """
        Return all users as a list of dicts: id, username, role, email (if present).
        """
        cursor = self.execute_query("SELECT id, username, role, status FROM users ORDER BY username")
        if cursor:
            return [
                {"id": row[0], "username": row[1], "role": row[2], "status": row[3], "email": ""} for row in cursor.fetchall()
            ]
        return []

    def get_users(self, search: str = "", sort: str = "username", order: str = "asc", limit: int = 20, offset: int = 0) -> List[Dict[str, Any]]:
        valid_sort = sort if sort in ["username", "role", "id"] else "username"
        valid_order = order if order in ["asc", "desc"] else "asc"
        query = f"SELECT id, username, role, status FROM users"
        params = []
        if search:
            query += " WHERE username LIKE ? OR role LIKE ?"
            params.extend([f"%{search}%", f"%{search}%"])
        query += f" ORDER BY {valid_sort} {valid_order} LIMIT ? OFFSET ?"
        params.extend([limit, offset])
        cursor = self.execute_query(query, tuple(params))
        if cursor:
            return [
                {"id": row[0], "username": row[1], "role": row[2], "status": row[3], "email": ""} for row in cursor.fetchall()
            ]
        return []

    def delete_user(self, user_id: int) -> None:
        """
        Delete a user by id.
        """
        try:
            self.execute_query("DELETE FROM users WHERE id=?", (user_id,))
        except Exception as e:
            print(f"❌ Error deleting user {user_id}: {e}")
    """
    Class for advanced database operations.
    Provides methods for executing queries, managing connection lifecycle,
    and dashboard convenience methods.
    """

    def __init__(self, db_path: str = DB_FILE):
        """
        Initialize the database handler. Opens a connection.
        """
        self.db_path = db_path
        self.conn: Optional[sqlite3.Connection] = connect_db(db_path)

    def __enter__(self) -> "DBHandler":
        """
        Context manager enter. Ensures DB connection is available.
        """
        if self.conn is None:
            self.conn = connect_db(self.db_path)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """
        Context manager exit. Closes the DB connection.
        """
        self.close()

    def close(self) -> None:
        """
        Close the database connection.
        """
        if self.conn:
            self.conn.close()
            self.conn = None

    def execute_query(self, query: str, params: Optional[Tuple[Any, ...]] = None) -> Optional[sqlite3.Cursor]:
        """
        Execute a SQL query with optional parameters.
        Returns the cursor, or None on error.
        """
        if self.conn is None:
            self.conn = connect_db(self.db_path)
        if self.conn is None:
            print("❌ No database connection available.")
            return None
        try:
            cursor = self.conn.cursor()
            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)
            self.conn.commit()
            return cursor
        except sqlite3.Error as e:
            print(f"❌ Query failed: {e}\nQuery: {query}\nParams: {params}")
            return None

    def fetch_all(self, query: str, params: Optional[Tuple[Any, ...]] = None) -> List[Tuple]:
        """
        Run a SELECT query and return all results as a list of tuples.
        Returns empty list on error.
        """
        cursor = self.execute_query(query, params)
        return cursor.fetchall() if cursor else []

    def fetch_one(self, query: str, params: Optional[Tuple[Any, ...]] = None) -> Optional[Tuple]:
        """
        Run a SELECT query and return a single result tuple, or None if none found.
        """
        cursor = self.execute_query(query, params)
        return cursor.fetchone() if cursor else None

    # --- Dashboard Utility Methods ---

    def get_farms(self) -> List[Dict[str, Any]]:
        """
        Get all farms as a list of dictionaries.
        Returns: List[Dict[str, Any]]
        """
        cursor = self.execute_query("SELECT id, name, location, base_temp FROM farms ORDER BY name")
        if cursor:
            return [
                {"id": row[0], "name": row[1], "location": row[2], "base_temp": row[3]}
                for row in cursor.fetchall()
            ]
        return []

    def get_climate_data(self, farm_id: int, limit: int = 20) -> List[Dict[str, Any]]:
        """
        Get up to `limit` rows of climate_data + agri_metrics for a farm, as list of dicts.
        Returns: List[Dict[str, Any]]
        """
        cursor = self.execute_query(
            """
            SELECT c.date, c.temp_max, c.temp_min, c.rainfall,
                   m.daily_gdd, m.effective_rainfall, m.cumulative_gdd
            FROM climate_data c
            LEFT JOIN agri_metrics m ON c.farm_id = m.farm_id AND c.date = m.date
            WHERE c.farm_id=?
            ORDER BY c.date ASC LIMIT ?
            """, (farm_id, limit)
        )
        keys = ["date", "temp_max", "temp_min", "rainfall", "daily_gdd", "effective_rainfall", "cumulative_gdd"]
        if cursor:
            return [dict(zip(keys, row)) for row in cursor.fetchall()]
        return []

    def get_farm_summary(self, farm_id: int) -> Dict[str, Union[float, None]]:
        """
        Get summary statistics for a farm:
        - avg_temp: Average of max temps
        - min_temp: Minimum of min temps
        - max_temp: Maximum of max temps
        - total_rain: Total rainfall
        - cumulative_gdd: Most recent cumulative GDD
        Returns: Dict[str, float or None]
        """
        results = self.fetch_one(
            """
            SELECT AVG(c.temp_max), MIN(c.temp_min), MAX(c.temp_max), SUM(c.rainfall),
                   (SELECT cumulative_gdd FROM agri_metrics WHERE farm_id=? ORDER BY date DESC LIMIT 1)
            FROM climate_data c WHERE c.farm_id=?
            """, (farm_id, farm_id)
        )
        if results:
            avg_temp, min_temp, max_temp, total_rain, latest_gdd = results
            return {
                "avg_temp": avg_temp,
                "min_temp": min_temp,
                "max_temp": max_temp,
                "total_rain": total_rain,
                "cumulative_gdd": latest_gdd
            }
        return {}

    def import_csv(self, csv_path: str, table: str, fieldnames: List[str], type_map: Optional[Dict[str, type]] = None) -> int:
        """
        Bulk import data from a CSV file into the specified table, with validation.
        Returns number of rows inserted. Logs and skips invalid rows.
        type_map: Optional dict of fieldname to type (e.g., {"temp_max": float})
        """
        import logging
        inserted = 0
        errors = []
        try:
            with open(csv_path, "r", newline="") as f:
                reader = csv.DictReader(f)
                # Validate headers
                csv_fields = reader.fieldnames
                if not csv_fields:
                    logging.error("CSV file is empty or missing headers.")
                    return 0
                missing = [f for f in fieldnames if f not in csv_fields]
                extra = [f for f in csv_fields if f not in fieldnames]
                if missing:
                    logging.error(f"CSV missing required fields: {missing}")
                    return 0
                if extra:
                    logging.warning(f"CSV has extra fields: {extra}")
                placeholders = ",".join("?" for _ in fieldnames)
                for i, row in enumerate(reader, 1):
                    try:
                        values = []
                        for field in fieldnames:
                            val = row[field]
                            if type_map and field in type_map:
                                try:
                                    val = type_map[field](val) if val != '' else None
                                except Exception:
                                    raise ValueError(f"Row {i}: Field '{field}' value '{val}' is not {type_map[field].__name__}")
                            values.append(val)
                        self.execute_query(
                            f"INSERT INTO {table} ({', '.join(fieldnames)}) VALUES ({placeholders})",
                            tuple(values)
                        )
                        inserted += 1
                    except Exception as e:
                        error_msg = f"Row {i} skipped: {e}"
                        errors.append(error_msg)
                        logging.error(error_msg)
                if self.conn:
                    self.conn.commit()
                else:
                    logging.error("❌ Cannot commit: No database connection available.")
        except Exception as e:
            logging.error(f"❌ CSV import failed: {e}")
        if errors:
            print(f"CSV import completed with {len(errors)} errors. See log for details.")
        return inserted

    def export_csv(self, query: str, params: Optional[Tuple[Any, ...]], out_path: str) -> int:
        """
        Export data from a SELECT query to a CSV file. Returns row count written.
        """
        try:
            cursor = self.execute_query(query, params)
            if cursor:
                rows = cursor.fetchall()
                colnames = [desc[0] for desc in cursor.description]
                with open(out_path, "w", newline="") as f:
                    writer = csv.writer(f)
                    writer.writerow(colnames)
                    writer.writerows(rows)
                return len(rows)
            return 0
        except Exception as e:
            print(f"❌ CSV export failed: {e}")
            return 0

    def delete_farm(self, farm_id: int) -> None:
        """
        Delete a farm and all associated climate and agri_metrics data.
        """
        try:
            self.execute_query("DELETE FROM agri_metrics WHERE farm_id=?", (farm_id,))
            self.execute_query("DELETE FROM climate_data WHERE farm_id=?", (farm_id,))
            self.execute_query("DELETE FROM farms WHERE id=?", (farm_id,))
        except Exception as e:
            print(f"❌ Error deleting farm {farm_id}: {e}")

    def delete_data_entry(self, farm_id: int, date: str) -> None:
        """
        Delete a specific climate/agri data entry by farm and date.
        """
        try:
            self.execute_query("DELETE FROM agri_metrics WHERE farm_id=? AND date=?", (farm_id, date))
            self.execute_query("DELETE FROM climate_data WHERE farm_id=? AND date=?", (farm_id, date))
        except Exception as e:
            print(f"❌ Error deleting entry for farm {farm_id} date {date}: {e}")