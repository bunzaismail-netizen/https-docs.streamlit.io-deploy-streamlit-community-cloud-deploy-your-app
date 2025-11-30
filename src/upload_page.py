import tkinter as tk
import ttkbootstrap as tb
from tkinter import messagebox, filedialog
import csv
import threading
try:
    import socketio
    _HAS_SOCKETIO = True
except Exception:
    socketio = None
    _HAS_SOCKETIO = False
from db_handler import DBHandler
from notifications import notify
from datetime import datetime
import os

AUDIT_LOG_FILE = "upload_audit_log.csv"  # Persistent audit log file

# Use the central notifications.notify to broadcast events

class UploadPage(tb.Frame):

    def safe_ui_update(self, func, *args, **kwargs):
        try:
            if getattr(self, '_shutdown', False):
                return
            if getattr(self, 'winfo_exists', lambda: False)():
                aft = getattr(self, 'after', None)
                if callable(aft):
                    try:
                        aft(0, lambda: func(*args, **kwargs))
                    except Exception:
                        try:
                            func(*args, **kwargs)
                        except Exception:
                            pass
                else:
                    try:
                        func(*args, **kwargs)
                    except Exception:
                        pass
        except Exception:
            pass
    def load_farms(self):
        with DBHandler() as db:
            farms = db.get_farms()
        self.farm_combo["values"] = [f"{f['name']} ({f['location']})" for f in farms]
        self.farm_ids = [f["id"] for f in farms]
        if self.farm_ids:
            self.farm_combo.current(0)
            self.selected_farm_id = self.farm_ids[0]
        else:
            self.selected_farm_id = None
    """
    Upload data page:
        - CSV file selection and upload (with template download)
        - Target farm selection
        - Import preview, per-row validation, persistent audit logs
        - Progress bar for import
        - Notifications, sidebar hooks, server/cloud (stub)
        - Live backend sync (socket.io)
        - Role/user aware
    """
    CSV_FIELDS = ["date", "temp_max", "temp_min", "rainfall", "daily_gdd", "eff_rain", "cum_gdd"]

    def __init__(self, parent, sidebar=None, user=None):
        super().__init__(parent)
        self.parent = parent
        self.user = user or {"username": "Guest", "role": "user"}
        self.backend_url = "http://localhost:8080"

        # Main content area only
        self.main = tb.Frame(self)
        self.main.pack(fill="both", expand=True, padx=12, pady=8)

        # Section: Farm selection
        farm_frame = tb.Frame(self.main)
        farm_frame.grid(row=0, column=0, sticky="w", pady=(0,10))
        tb.Label(farm_frame, text="Target Farm:", font=("Segoe UI", 12, "bold"), foreground="#636e72").grid(row=0, column=0, sticky="w")
        self.farm_combo = tb.Combobox(farm_frame, width=30, state="readonly")
        self.farm_combo.grid(row=0, column=1, padx=10)

        # Section: File selection & template
        file_frame = tb.Frame(self.main)
        file_frame.grid(row=1, column=0, sticky="w", pady=(0,8))
        tb.Button(file_frame, text="Select CSV File", command=self.select_file).grid(row=0, column=0, padx=8)
        tb.Button(file_frame, text="Download CSV Template", command=self.download_template).grid(row=0, column=1, padx=8)
        tb.Button(file_frame, text="Cloud Upload (stub)", command=self.cloud_upload_stub).grid(row=0, column=2, padx=8)
        self.file_label = tk.Label(file_frame, text="No file selected", font=("Segoe UI", 9))
        self.file_label.grid(row=0, column=3, padx=8)

        # Section: Preview area
        preview_frame = tb.LabelFrame(self.main, text="Preview (first 5 rows)")
        preview_frame.grid(row=2, column=0, sticky="ew", padx=10, pady=8)
        self.preview_text = tk.Text(preview_frame, width=100, height=8, font=("Consolas", 10), wrap="none")
        self.preview_text.grid(row=0, column=0, sticky="nsew")

        # Section: Progress bar
        prog_frame = tb.Frame(self.main)
        prog_frame.grid(row=3, column=0, sticky="ew", padx=10, pady=(2,2))
        self.import_progress = tb.Progressbar(prog_frame, orient="horizontal", mode="determinate", length=320)
        self.import_progress.grid(row=0, column=0, padx=6)
        self.prog_label = tk.Label(prog_frame, text="", font=("Segoe UI", 9))
        self.prog_label.grid(row=0, column=1, padx=8)

        # Section: Import and audit
        import_frame = tb.Frame(self.main)
        import_frame.grid(row=4, column=0, sticky="w", pady=10)
        tb.Button(import_frame, text="Import Data", width=16, command=self.import_data).grid(row=0, column=0, padx=4)
        tb.Button(import_frame, text="Show Audit History", width=18, command=self.show_audit_history).grid(row=0, column=1, padx=4)
        tb.Button(import_frame, text="Refresh Farms", width=14, command=self.load_farms).grid(row=0, column=2, padx=4)

        # Data & audit
        self.farm_ids = []
        self.selected_farm_id = None
        self.selected_file = None
        self.preview_rows = []
        self.audit_trail = []
        # socket attributes (may be None if python-socketio is not installed)
        self.socketio_client = None
        self.socket_thread = None
        self.sync_label = tk.Label(self, text="⏳ Not synced", font=("Segoe UI", 9), fg="#ff99cc")
        self.sync_label.pack(anchor="ne", pady=(0,2), padx=12)
        self.load_farms()
        self.farm_combo.bind("<<ComboboxSelected>>", self.on_farm_selected)
        self.load_persistent_audit_trail()

        # Load farm values
        with DBHandler() as db:
            farms = db.get_farms()
        self.farm_combo["values"] = [f"{f['name']} ({f['location']})" for f in farms]
        self.farm_ids = [f["id"] for f in farms]
        if self.farm_ids:
            self.farm_combo.current(0)
            self.selected_farm_id = self.farm_ids[0]
        else:
            self.selected_farm_id = None

    def on_farm_selected(self, event=None):
        idx = self.farm_combo.current()
        if idx < 0 or idx >= len(self.farm_ids):
            self.selected_farm_id = None
        else:
            self.selected_farm_id = self.farm_ids[idx]

    def select_file(self):
        file_path = filedialog.askopenfilename(
            title="Select CSV File",
            filetypes=[("CSV Files", "*.csv"), ("All Files", "*.*")]
        )
        if not self.winfo_exists():
            return
        if not file_path:
            self.selected_file = None
            if self.winfo_exists():
                self.file_label.config(text="No file selected")
            self.preview_text.delete("1.0", tk.END)
            return
        self.selected_file = file_path
        if self.winfo_exists():
            self.file_label.config(text=os.path.basename(file_path))
        self.preview_csv(file_path)

    def preview_csv(self, file_path):
        self.preview_rows = []
        self.preview_text.delete("1.0", tk.END)
        try:
            with open(file_path, "r", newline="") as f:
                reader = csv.DictReader(f)
                header = reader.fieldnames
                if not self.validate_csv_header(header):
                    self.preview_text.insert(tk.END, f"Header error: CSV must contain fields: {', '.join(self.CSV_FIELDS)}\n")
                    return
                if header:
                    self.preview_text.insert(tk.END, ",".join(header) + "\n")
                for i, row in enumerate(reader):
                    self.preview_rows.append(row)
                    errors = self.validate_row(row, header)
                    preview_line = ",".join([row.get(col, "") for col in header]) if header else ""
                    if errors:
                        preview_line += "   <-- " + "; ".join(errors)
                    self.preview_text.insert(tk.END, preview_line + "\n")
                    if i >= 4: break
        except Exception as e:
            self.preview_text.insert(tk.END, f"Preview failed: {e}")

    def validate_csv_header(self, header):
        # Check for all required fields
        return all(f in header for f in self.CSV_FIELDS)

    def validate_row(self, row, header=None):
        # Validate date and numeric fields; returns list of errors
        errors = []
        date = row.get("date", "")
        try:
            datetime.strptime(date, "%Y-%m-%d")
        except Exception:
            errors.append("Invalid date")
        for f in self.CSV_FIELDS[1:]:
            val = row.get(f, "")
            try:
                float(val)
            except Exception:
                errors.append(f"Invalid {f}")
        return errors

    def download_template(self):
        file_path = filedialog.asksaveasfilename(
            title="Save CSV Template",
            defaultextension=".csv",
            filetypes=[("CSV Files", "*.csv"), ("All Files", "*.*")]
        )
        if not file_path:
            return
        try:
            with open(file_path, "w", newline="") as f:
                writer = csv.DictWriter(f, fieldnames=self.CSV_FIELDS)
                writer.writeheader()
                writer.writerow({
                    "date": "2025-09-01",
                    "temp_max": 32.5,
                    "temp_min": 21.7,
                    "rainfall": 12.3,
                    "daily_gdd": 17.5,
                    "eff_rain": 10.0,
                    "cum_gdd": 214.0
                })
            messagebox.showinfo("Download", f"Template saved as {file_path}")
        except Exception as e:
            messagebox.showerror("Download Error", f"Failed to save template: {e}")

    def import_data(self):
        if not self.selected_farm_id:
            messagebox.showwarning("Import", "Please select a target farm.")
            return
        if not self.selected_file:
            messagebox.showwarning("Import", "Please select a CSV file to import.")
            return
        try:
            with open(self.selected_file, "r", newline="") as f:
                reader = list(csv.DictReader(f))
                header = reader[0].keys() if reader else self.CSV_FIELDS
        except Exception as e:
            messagebox.showerror("Import Error", f"Failed to read file: {e}")
            return
        if not self.validate_csv_header(header):
            messagebox.showerror("Import Error", f"CSV file must have columns: {', '.join(self.CSV_FIELDS)}")
            return
        total = len(reader)
        if total == 0:
            messagebox.showerror("Import Error", "CSV file contains no data.")
            return
        self.import_progress["maximum"] = total
        self.import_progress["value"] = 0
        self.prog_label.config(text=f"0/{total}")

        # Do import in thread to avoid UI block
        def import_thread():
            count = 0
            errors = []
            for i, row in enumerate(reader):
                row_errors = self.validate_row(row, header)
                if row_errors:
                    errors.append(f"Row {i+1}: {'; '.join(row_errors)}")
                    continue
                try:
                    date = row.get("date")
                    temp_max = float(row.get("temp_max", 0))
                    temp_min = float(row.get("temp_min", 0))
                    rainfall = float(row.get("rainfall", 0))
                    daily_gdd = float(row.get("daily_gdd", 0))
                    eff_rain = float(row.get("eff_rain", 0))
                    cum_gdd = float(row.get("cum_gdd", 0))
                    with DBHandler() as db:
                        db.execute_query(
                            "INSERT OR REPLACE INTO climate_data (farm_id, date, temp_max, temp_min, rainfall) VALUES (?, ?, ?, ?, ?)",
                            (self.selected_farm_id, date, temp_max, temp_min, rainfall)
                        )
                        db.execute_query(
                            "INSERT OR REPLACE INTO agri_metrics (farm_id, date, daily_gdd, effective_rainfall, cumulative_gdd) VALUES (?, ?, ?, ?, ?)",
                            (self.selected_farm_id, date, daily_gdd, eff_rain, cum_gdd)
                        )
                    count += 1
                except Exception as e:
                    errors.append(f"Row {i+1}: {e}")
                # Update progress bar on UI thread
                self.safe_ui_update(self.import_progress.config, value=i+1)
                self.safe_ui_update(self.prog_label.config, text=f"{i+1}/{total}")
                notify("progress", f"Import progress: {i+1}/{total}")
            self.safe_ui_update(self.import_progress.config, value=0)
            self.safe_ui_update(self.prog_label.config, text="")
            self._audit("import", f"{count} entries imported by {self.user['username']} to farm {self.selected_farm_id}.")
            notify("import", f"{count} entries uploaded by {self.user['username']}.")
            msg = f"Imported {count} entries."
            if errors:
                msg += f"\n{len(errors)} rows skipped due to errors."
            self.safe_ui_update(messagebox.showinfo, "Import", msg)
            self.save_persistent_audit_trail()
        threading.Thread(target=import_thread, daemon=True).start()

    # --- Cloud/server upload stub ---
    def cloud_upload_stub(self):
        if not self.selected_file:
            messagebox.showwarning("Cloud Upload", "Please select a CSV file to upload.")
            return
        # Simulate cloud upload (integrate requests or boto3 as needed)
        messagebox.showinfo("Cloud Upload", "Stub: Cloud upload integration goes here.\nIntegrate with your API/S3 as needed.")

    def _audit(self, action_type, msg):
        record = {
            "timestamp": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"),
            "user": self.user.get("username", "Guest"),
            "action": action_type,
            "message": msg
        }
        self.audit_trail.append(record)
        # Use the central notifications dispatcher (notify) so background threads
        # can broadcast events to the UI safely. Previously this called
        # `backend_event_notification` which may not be defined, causing a
        # NameError when invoked from a worker thread.
        try:
            notify(action_type, msg)
        except Exception:
            # Best-effort: if notifications fail, continue without raising.
            pass

    def show_audit_history(self):
        top = tk.Toplevel(self)
        top.title("Upload Audit History")
        text = tk.Text(top, width=80, height=18, font=("Consolas", 10))
        text.pack(fill="both", expand=True)
        for rec in self.audit_trail:
            text.insert(tk.END, f"{rec['timestamp']} | {rec['user']} | {rec['action']} | {rec['message']}\n")
        text.config(state="disabled")
        tb.Button(top, text="Close", command=top.destroy).pack(pady=8)

    def save_persistent_audit_trail(self):
        # Save audit logs to persistent file
        if not self.audit_trail:
            return
        exists = os.path.isfile(AUDIT_LOG_FILE)
        with open(AUDIT_LOG_FILE, "a", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=["timestamp", "user", "action", "message"])
            if not exists:
                writer.writeheader()
            for rec in self.audit_trail:
                writer.writerow(rec)
        self.audit_trail.clear()

    def load_persistent_audit_trail(self):
        if not os.path.isfile(AUDIT_LOG_FILE):
            return
        try:
            with open(AUDIT_LOG_FILE, "r", newline="") as f:
                reader = csv.DictReader(f)
                self.audit_trail = list(reader)
        except Exception:
            self.audit_trail = []

    # --- Live backend sync (socket.io) ---
    def start_socket_listener(self):
        # If socket.io is not available in the environment, skip starting the listener
        if not _HAS_SOCKETIO:
            try:
                self.safe_ui_update(lambda: self.sync_label.config(text="⚠ Socket not available"))
            except Exception:
                pass
            return

        def listen():
            try:
                # import socketio lazily here so static analyzers know this code path
                try:
                    import socketio as _socketio
                except Exception:
                    self.safe_ui_update(lambda: self.sync_label.config(text="⚠ Socket not available"))
                    return
                client = _socketio.Client()

                @client.event
                def connect():
                    # Marshal to main thread
                    self.safe_ui_update(lambda: self.sync_label.config(text="🟢 Live Sync"))

                @client.event
                def disconnect():
                    self.safe_ui_update(lambda: self.sync_label.config(text="🔴 Disconnected"))

                def on_update(data):
                    msg = data.get("msg", "Backend data updated")
                    notify("backend", msg)
                    self.safe_ui_update(lambda: self.sync_label.config(text="🔄 Refreshed from backend"))

                client.on("update", on_update)
                # store client reference so stop_socket can access it
                self.socketio_client = client
                client.connect(self.backend_url)
                client.wait()
            except Exception as e:
                self.safe_ui_update(lambda: self.sync_label.config(text="⚠️ Socket Error"))
                notify("socket", f"Socket error: {e}")
        self.socket_thread = threading.Thread(target=listen, daemon=True)
        self.socket_thread.start()

    def stop_socket(self):
        """Disconnect socket client and mark shutdown to stop the listener thread."""
        try:
            self._shutdown = True
        except Exception:
            pass
        try:
            # If socketio is not available, nothing to do
            if not _HAS_SOCKETIO:
                return
            # If we have a socketio client instance, try to disconnect it
            sio = getattr(self, 'socketio_client', None)
            if sio is not None:
                try:
                    sio.disconnect()
                except Exception:
                    pass
        except Exception:
            pass

    def get_frame(self):
        return self
