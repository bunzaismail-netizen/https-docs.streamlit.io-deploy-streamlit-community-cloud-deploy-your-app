import tkinter as tk
import ttkbootstrap as tb
from tkinter import filedialog, messagebox, simpledialog
from db_handler import DBHandler
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import pandas as pd
import csv
import os
import numpy as np
from datetime import datetime, timedelta
import threading

class ReportPage(tb.Frame):
    """
    Page for generating, viewing, and exporting climate/agri reports.
    Features:
      - Multiple analytics (trend, correlation, outlier, rolling mean, farm comparison, anomaly detection)
      - Scheduling (auto/scheduled reports)
      - Multi-user logic (report access by user, user filtering)
      - Custom report templates, multi-metric plots, export to CSV/PDF/cloud.
      - Admin tools for all-user/global analytics
    """

    def __init__(self, parent, user=None):
        super().__init__(parent)
        self.parent = parent
        self.current_user = user or {"username": "Guest"}

        # Main content area only
        self.main = tb.Frame(self)
        self.main.pack(fill="both", expand=True, padx=12, pady=8)

        # Section: Farm selector
        farm_frame = tb.Frame(self.main)
        farm_frame.pack(anchor="w", pady=(0, 12))
        tb.Label(farm_frame, text="Select Farm(s):", font=("Segoe UI", 12)).pack(side="left")
        self.farm_listbox = tk.Listbox(farm_frame, selectmode="multiple", width=36, height=4)
        self.farm_listbox.pack(side="left", padx=10)
        self.load_farms()

        # Section: User selection (for admins)
        user_frame = tb.Frame(self.main)
        user_frame.pack(anchor="w", pady=(0, 8))
        tb.Label(user_frame, text="Report User:", font=("Segoe UI", 10)).pack(side="left")
        self.user_var = tk.StringVar(value=self.current_user['username'])
        self.user_combo = tb.Combobox(user_frame, values=[], textvariable=self.user_var, width=18, state="readonly")
        self.user_combo.pack(side="left", padx=7)
        self.user_combo.bind("<<ComboboxSelected>>", self.on_user_selected)
        self.load_users()

        # Section: Date range input
        date_frame = tb.Frame(self.main)
        date_frame.pack(anchor="w", pady=(0, 12))
        tb.Label(date_frame, text="Start Date (YYYY-MM-DD):").pack(side="left", padx=2)
        self.start_date_var = tk.StringVar()
        tb.Entry(date_frame, textvariable=self.start_date_var, width=12).pack(side="left", padx=5)
        tb.Label(date_frame, text="End Date (YYYY-MM-DD):").pack(side="left", padx=2)
        self.end_date_var = tk.StringVar()
        tb.Entry(date_frame, textvariable=self.end_date_var, width=12).pack(side="left", padx=5)

        # Section: Template selection
        template_frame = tb.Frame(self.main)
        template_frame.pack(anchor="w", pady=(0, 10))
        tb.Label(template_frame, text="Report Template:", font=("Segoe UI", 12)).pack(side="left")
        self.template_var = tk.StringVar(value="Standard")
        templates = [
            "Standard", 
            "Yield Focused", 
            "Climate Trends", 
            "Customize...", 
            "Minimal (farm, date, temp_max)", 
            "Rainfall Only",
            "Anomaly Detection"
        ]
        self.template_combo = tb.Combobox(template_frame, values=templates, textvariable=self.template_var, state="readonly", width=22)
        self.template_combo.pack(side="left", padx=8)
        self.template_combo.bind("<<ComboboxSelected>>", self.handle_custom_template)

        # Section: Scheduling
        sched_frame = tb.Frame(self.main)
        sched_frame.pack(anchor="w", pady=5)
        tb.Label(sched_frame, text="Schedule Report Every (minutes):", font=("Segoe UI", 10)).pack(side="left")
        self.sched_var = tk.StringVar(value="0")
        tb.Entry(sched_frame, textvariable=self.sched_var, width=5).pack(side="left", padx=5)
        tb.Button(sched_frame, text="Start", width=8, command=self.start_schedule).pack(side="left", padx=4)
        tb.Button(sched_frame, text="Stop", width=8, command=self.stop_schedule).pack(side="left", padx=4)
        self.sched_running = False
        self.sched_thread = None


        # Section: Action buttons
        btn_frame = tb.Frame(self.main)
        btn_frame.pack(anchor="w", pady=10)
        tb.Button(btn_frame, text="Generate Report", width=18, command=self.generate_report).pack(side="left", padx=5)
        tb.Button(btn_frame, text="Export CSV", width=14, command=self.export_csv).pack(side="left", padx=5)
        tb.Button(btn_frame, text="Export PDF", width=14, command=self.export_pdf).pack(side="left", padx=5)
        tb.Button(btn_frame, text="Export to Cloud", width=18, command=self.export_cloud).pack(side="left", padx=5)
        tb.Button(btn_frame, text="Analytics", width=13, command=self.show_analytics).pack(side="left", padx=5)
        tb.Button(btn_frame, text="Global Analytics", width=16, command=self.global_analytics).pack(side="left", padx=5)

        # Section: Summary stats
        self.summary_label = tb.Label(self.main, text="", font=("Segoe UI", 11, "bold"))
        self.summary_label.pack(pady=8)
        # Section: Plot area (defer creation until page is visible)
        self.fig = None
        self.ax = None
        self.canvas = None
        self._initialized = False
        self._shutdown = False

        # Section: Table (results)
        self.table = tk.Text(self.main, height=8, width=110, font=("Consolas", 10), wrap="none")
        self.table.pack(pady=8, fill="x")

        # Data cache
        self.report_data = []
        self.custom_fields = None

        # Cloud API key
        self.cloud_api_key = None

        # Anomaly detection config
        self.anomaly_z = 2.5

    # ---- Multi-user logic ----
    def load_users(self):
        """Load available users for report selection (admin only)."""
        # Example: replace with real user DB call
        users = ["admin", "alice", "bob", "charlie", self.current_user.get('username', "Guest")]
        users = list(sorted(set(users)))
        self.user_combo["values"] = users
        self.user_combo.set(self.current_user.get('username', "Guest"))

    def on_user_selected(self, event=None):
        self.current_user['username'] = self.user_var.get()
        self.load_farms()  # Optionally filter farms by user

    def load_farms(self):
        """Load farms for reporting, optionally filter by user."""
        self.farm_listbox.delete(0, tk.END)
        with DBHandler() as db:
            farms = db.get_farms()
        # Example: filter farms by user (add logic as needed)
        filtered = [f for f in farms if self.current_user.get('username', '') == "admin" or f['name'].startswith(self.current_user.get('username', '')[0].upper()) or True]
        self.farm_map = {}
        for i, farm in enumerate(filtered):
            label = f"{farm['name']} ({farm['location']})"
            self.farm_listbox.insert(tk.END, label)
            self.farm_map[i] = farm["id"]

    def get_selected_farms(self):
        selection = self.farm_listbox.curselection()
        return [self.farm_map[i] for i in selection]

    # ---- Template Logic ----
    def handle_custom_template(self, event=None):
        t = self.template_var.get()
        if t == "Customize...":
            fields = simpledialog.askstring("Custom Template", "Enter comma-separated fields (e.g. date,temp_max,rainfall):")
            if fields:
                self.custom_fields = [f.strip() for f in fields.split(",")]
            else:
                self.template_var.set("Standard")
                self.custom_fields = None
        elif t == "Minimal (farm, date, temp_max)":
            self.custom_fields = ["date", "temp_max"]
        elif t == "Rainfall Only":
            self.custom_fields = ["date", "rainfall"]
        elif t == "Anomaly Detection":
            self.custom_fields = ["date", "temp_max", "rainfall", "cumulative_gdd"]
        else:
            self.custom_fields = None

    def get_template_fields(self):
        if self.custom_fields:
            return self.custom_fields
        t = self.template_var.get()
        if t == "Yield Focused":
            return ["date", "temp_max", "rainfall", "cumulative_gdd"]
        elif t == "Climate Trends":
            return ["date", "temp_max", "temp_min", "rainfall"]
        elif t == "Anomaly Detection":
            return ["date", "temp_max", "rainfall", "cumulative_gdd"]
        else:  # Standard
            return ["date", "temp_max", "temp_min", "rainfall", "daily_gdd", "effective_rainfall", "cumulative_gdd"]

    # ---- Scheduling Logic ----
    def start_schedule(self):
        if self.sched_running:
            messagebox.showinfo("Schedule", "Scheduling already running.")
            return
        try:
            minutes = int(self.sched_var.get())
            if minutes <= 0:
                raise ValueError
        except Exception:
            messagebox.showerror("Schedule", "Enter a positive integer for minutes.")
            return
        self.sched_running = True
        self.sched_thread = threading.Thread(target=self.schedule_worker, args=(minutes,), daemon=True)
        self.sched_thread.start()
        self.safe_ui_update(messagebox.showinfo, "Schedule", f"Auto-report generation started (every {minutes} min).")

    def on_show(self):
        if getattr(self, '_initialized', False):
            return
        try:
            self.fig, self.ax = plt.subplots(figsize=(5, 3.5))
            self.canvas = FigureCanvasTkAgg(self.fig, master=self.main)
            w = getattr(self.canvas, 'get_tk_widget', lambda: None)()
            if w:
                try:
                    w.pack(pady=10)
                except Exception:
                    pass
            try:
                self.fig.tight_layout()
            except Exception:
                pass
            self._initialized = True
        except Exception:
            pass

    def safe_ui_update(self, func, *args, **kwargs):
        try:
            if not getattr(self, '_shutdown', False) and getattr(self, 'winfo_exists', lambda: False)():
                aft = getattr(self, 'after', None)
                if callable(aft):
                    try:
                        aft(0, lambda: func(*args, **kwargs))
                    except Exception:
                        # fallback to direct call if after fails (best-effort)
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

    def destroy(self):
        self._shutdown = True
        try:
            canvas = getattr(self, 'canvas', None)
            if canvas is not None:
                try:
                    getter = getattr(canvas, 'get_tk_widget', None)
                    if getter:
                        w = getter()
                        if w:
                            w.destroy()
                except Exception:
                    pass
        except Exception:
            pass
        super().destroy()

    def stop_schedule(self):
        self.sched_running = False
        self.safe_ui_update(messagebox.showinfo, "Schedule", "Auto-report generation stopped.")

    def schedule_worker(self, minutes):
        # Do not call any Tk methods from this background thread (winfo_exists, etc.).
        # Rely on the _shutdown flag and safe_ui_update to marshal UI calls.
        while self.sched_running and not getattr(self, '_shutdown', False):
            try:
                # Marshal the report generation to the main thread; safe_ui_update will
                # check widget existence and _shutdown before calling.
                self.safe_ui_update(self.generate_report)
            except Exception:
                # swallow exceptions from scheduling to keep loop alive until stopped
                pass
            # Sleep for the requested interval, but check the shutdown flag each second
            for _ in range(max(1, minutes * 60)):
                if not self.sched_running or getattr(self, '_shutdown', False):
                    break
                threading.Event().wait(1)

    # ---- Report Generation, Export, Analytics ----
    def generate_report(self):
        if not self.winfo_exists():
            return
        farms = self.get_selected_farms()
        if not farms:
            self.safe_ui_update(messagebox.showwarning, "Report", "Select at least one farm.")
            return

        start_date = self.start_date_var.get().strip()
        end_date = self.end_date_var.get().strip()
        if start_date and end_date and start_date > end_date:
            self.safe_ui_update(messagebox.showerror, "Date Error", "Start date must be before end date.")
            return

        self.report_data.clear()
        self.safe_ui_update(self.table.delete, "1.0", tk.END)
        # If axes/canvas aren't initialized yet, lazily initialize them
        if not getattr(self, '_initialized', False):
            try:
                self.on_show()
            except Exception:
                pass
        ax = getattr(self, 'ax', None)
        if ax is not None:
            # capture ax in default arg to avoid None at call time
            self.safe_ui_update(lambda a=ax: a.clear())
        all_stats = []

        fields = self.get_template_fields()
        field_map = {
            "date": "c.date",
            "temp_max": "c.temp_max",
            "temp_min": "c.temp_min",
            "rainfall": "c.rainfall",
            "daily_gdd": "m.daily_gdd",
            "effective_rainfall": "m.effective_rainfall",
            "cumulative_gdd": "m.cumulative_gdd"
        }

        select_fields = [field_map.get(f, f) for f in fields]
        select_clause = ", ".join(select_fields)
        header = " | ".join([f.capitalize() for f in fields])

        with DBHandler() as db:
            for farm_id in farms:
                q = f"""SELECT {select_clause} FROM climate_data c
                        LEFT JOIN agri_metrics m ON c.farm_id = m.farm_id AND c.date = m.date
                        WHERE c.farm_id=?"""
                params = [farm_id]
                if start_date:
                    q += " AND c.date>=?"
                    params.append(start_date)
                if end_date:
                    q += " AND c.date<=?"
                    params.append(end_date)
                q += " ORDER BY c.date ASC"
                rows = db.fetch_all(q, tuple(params))
                if not rows:
                    continue
                farm_name = db.fetch_one("SELECT name FROM farms WHERE id=?", (farm_id,))
                farm_name = farm_name[0] if farm_name else "Farm"
                for row in rows:
                    entry = dict(zip(fields, row))
                    entry["farm"] = farm_name
                    entry["user"] = self.current_user.get("username", "N/A")
                    self.report_data.append(entry)
                # Analytics for summary
                arr = np.array(rows, dtype=float)
                if "temp_max" in fields:
                    avg_temp = np.nanmean(arr[:,fields.index("temp_max")]) if arr.size else 0
                else:
                    avg_temp = None
                if "rainfall" in fields:
                    total_rain = np.nansum(arr[:,fields.index("rainfall")]) if arr.size else 0
                else:
                    total_rain = None
                if "cumulative_gdd" in fields:
                    last_gdd = arr[-1,fields.index("cumulative_gdd")] if arr.size else 0
                else:
                    last_gdd = None
                s = f"{farm_name}:"
                if avg_temp is not None: s += f" Avg Tmax={avg_temp:.1f}°C"
                if total_rain is not None: s += f", Total Rain={total_rain:.1f}mm"
                if last_gdd is not None: s += f", Cum GDD={last_gdd:.1f}"
                all_stats.append(s)
                # Plot
                dates = [row[fields.index("date")] for row in rows]
                for i, f in enumerate(fields):
                    if f == "date":
                        continue
                    vals = [row[i] for row in rows]
                    ax = getattr(self, 'ax', None)
                    if self.winfo_exists() and ax is not None:
                        try:
                            ax.plot(dates, vals, marker="o", label=f"{farm_name} {f}")
                        except Exception:
                            pass

        if not self.report_data:
            self.safe_ui_update(self.summary_label.config, text="No data found for selection.")
            ax = getattr(self, 'ax', None)
            canvas = getattr(self, 'canvas', None)
            if ax is not None:
                self.safe_ui_update(lambda a=ax: a.text(0.5, 0.5, "No data", ha="center", va="center", fontsize=12))
            if canvas is not None:
                self.safe_ui_update(lambda c=canvas: c.draw())
            return

        # Table output
        table_header = f"{'Farm':<15} {'User':<10}" + " ".join([f"{h:<12}" for h in fields])
        self.table.insert(tk.END, table_header + "\n" + "-"*len(table_header) + "\n")
        for row in self.report_data:
            line = f"{row['farm']:<15} {row['user']:<10}" + " ".join([f"{row.get(f, '')!s:<12}" for f in fields])
            self.table.insert(tk.END, line + "\n")

        # Summary
        self.safe_ui_update(self.summary_label.config, text=" | ".join(all_stats))

        # Plot
        ax = getattr(self, 'ax', None)
        fig = getattr(self, 'fig', None)
        canvas = getattr(self, 'canvas', None)
        if ax is not None:
            self.safe_ui_update(lambda a=ax: a.set_title("Report Metrics Over Time"))
            self.safe_ui_update(lambda a=ax: a.set_xlabel("Date"))
            self.safe_ui_update(lambda a=ax: a.set_ylabel("Value"))
            self.safe_ui_update(lambda a=ax: a.legend())
        if fig is not None:
            self.safe_ui_update(lambda f=fig: f.autofmt_xdate(rotation=25))
        if canvas is not None:
            self.safe_ui_update(lambda c=canvas: c.draw())

    def export_csv(self):
        """Export current report data to CSV."""
        if not self.report_data:
            messagebox.showwarning("Export", "No report data to export.")
            return
        file_path = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV Files", "*.csv"), ("All Files", "*.*")]
        )
        if not file_path:
            return
        try:
            with open(file_path, "w", newline="") as f:
                writer = csv.DictWriter(f, fieldnames=list(self.report_data[0].keys()))
                writer.writeheader()
                for entry in self.report_data:
                    writer.writerow(entry)
            messagebox.showinfo("Export", f"Report exported to:\n{file_path}")
        except Exception as e:
            messagebox.showerror("Export Error", f"Failed to export report: {e}")

    def export_pdf(self):
        """Export current plot to PDF."""
        if not self.report_data:
            messagebox.showwarning("Export", "No report generated to export.")
            return
        file_path = filedialog.asksaveasfilename(
            defaultextension=".pdf",
            filetypes=[("PDF Files", "*.pdf"), ("All Files", "*.*")]
        )
        if not file_path:
            return
        try:
            from matplotlib.backends.backend_pdf import PdfPages
            with PdfPages(file_path) as pdf:
                pdf.savefig(self.fig)
            messagebox.showinfo("Export", f"Plot PDF exported to:\n{file_path}")
        except Exception as e:
            messagebox.showerror("Export Error", f"Failed to export PDF: {e}")

    def export_cloud(self):
        """Export report data to a cloud endpoint (with API key and error handling)."""
        if not self.report_data:
            messagebox.showwarning("Export", "No report data to export.")
            return
        try:
            try:
                import requests
            except ImportError:
                messagebox.showerror("Cloud Export", "The requests library is required.")
                return
        except ImportError:
            messagebox.showerror("Cloud Export", "The requests library is required.")
            return
        # Prompt for API key if not set
        if not self.cloud_api_key:
            key = simpledialog.askstring("Cloud Export", "Enter Cloud API Key:", show="*")
            if not key:
                return
            self.cloud_api_key = key.strip()
        api_url = "https://your-api-endpoint/report-upload"
        headers = {"Authorization": f"Bearer {self.cloud_api_key}"}
        import io
        buf = io.StringIO()
        writer = csv.DictWriter(buf, fieldnames=list(self.report_data[0].keys()))
        writer.writeheader()
        for entry in self.report_data:
            writer.writerow(entry)
        buf.seek(0)
        files = {"file": ("report.csv", buf.read())}
        try:
            response = requests.post(api_url, headers=headers, files=files, timeout=10)
            if response.status_code == 200:
                messagebox.showinfo("Cloud Export", f"Report uploaded successfully!\nResponse: {response.text}")
            elif response.status_code == 401:
                self.cloud_api_key = None
                messagebox.showerror("Cloud Export", "Unauthorized (invalid API key).")
            elif response.status_code == 429:
                messagebox.showerror("Cloud Export", "Rate limit exceeded, try later.")
            else:
                messagebox.showerror("Cloud Export", f"Error: {response.status_code}\n{response.text}")
        except Exception as e:
            messagebox.showerror("Cloud Export", f"Failed to upload: {e}")

    def show_analytics(self):
        """Show advanced analytics on the report data (trend, correlation, outlier, rolling mean, farm comparison, anomaly detection)."""
        if not self.report_data:
            messagebox.showinfo("Analytics", "No report data for analytics.")
            return
        import numpy as np
        import pandas as pd
        try:
            df = pd.DataFrame(self.report_data)
            numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
            analytic_str = "=== Analytics ===\n"
            # Correlation matrix
            if len(numeric_cols) >= 2:
                corr = df[numeric_cols].corr()
                analytic_str += "\nCorrelation Matrix:\n" + corr.round(2).to_string() + "\n"
            # Outlier detection (z-score > 2.5)
            for col in numeric_cols:
                vals = df[col]
                zscores = (vals - vals.mean())/vals.std(ddof=0) if vals.std(ddof=0) else np.zeros_like(vals)
                outliers = df[abs(zscores) > self.anomaly_z]
                if not outliers.empty:
                    analytic_str += f"\nOutliers in {col} (z>{self.anomaly_z}):\n"
                    analytic_str += outliers[["farm", "date", col]].to_string(index=False) + "\n"
            # Trend (rolling mean, if enough points)
            if "date" in df.columns and "temp_max" in df.columns and len(df) > 5:
                df["date"] = pd.to_datetime(df["date"])
                df.sort_values("date", inplace=True)
                df["temp_max_rm"] = df["temp_max"].rolling(window=3, min_periods=1).mean()
                analytic_str += "\nSample Rolling Mean of temp_max:\n"
                analytic_str += df[["date", "temp_max", "temp_max_rm"]].tail(5).to_string(index=False) + "\n"
            # Farm comparison
            if "farm" in df.columns and "temp_max" in df.columns:
                farm_means = df.groupby("farm")["temp_max"].mean()
                analytic_str += "\nMean temp_max by farm:\n" + farm_means.round(2).to_string() + "\n"
            # Anomaly detection (if template is Anomaly Detection)
            if self.template_var.get() == "Anomaly Detection":
                for col in ["temp_max", "rainfall", "cumulative_gdd"]:
                    if col in df.columns:
                        vals = np.array(df[col].values)
                        mean, std = np.nanmean(vals), np.nanstd(vals)
                        anomalies = df[np.abs(vals - mean) > self.anomaly_z*std]
                        if not anomalies.empty:
                            analytic_str += f"\nAnomalies in {col} (>|{self.anomaly_z}| std):\n"
                            analytic_str += anomalies[["farm", "date", col]].to_string(index=False) + "\n"
            # Display in popup
            top = tk.Toplevel(self)
            top.title("Advanced Analytics")
            text = tk.Text(top, width=110, height=30, font=("Consolas", 10))
            text.pack(fill="both", expand=True)
            text.insert(tk.END, analytic_str or "No analytics available.")
            text.config(state="disabled")
        except Exception as e:
            messagebox.showerror("Analytics", f"Failed to compute analytics: {e}")

    def global_analytics(self):
        """Show summary analytics for all users (admin tool)."""
        if self.current_user.get("username", "") != "admin":
            messagebox.showwarning("Global Analytics", "Admin access required.")
            return
        import numpy as np
        import pandas as pd
        try:
            with DBHandler() as db:
                farms = db.get_farms()
                allrows = []
                for farm in farms:
                    farm_id = farm["id"]
                    rows = db.fetch_all(
                        "SELECT date, temp_max, temp_min, rainfall, cumulative_gdd FROM climate_data WHERE farm_id=? ORDER BY date ASC",
                        (farm_id,)
                    )
                    for row in rows:
                        entry = dict(date=row[0], temp_max=row[1], temp_min=row[2], rainfall=row[3], cumulative_gdd=row[4], farm=farm["name"])
                        allrows.append(entry)
            if not allrows:
                messagebox.showinfo("Global Analytics", "No data for analytics.")
                return
            df = pd.DataFrame(allrows)
            analytic_str = "=== Global Analytics ===\n"
            if "temp_max" in df.columns and "farm" in df.columns:
                farm_means = df.groupby("farm")["temp_max"].mean()
                analytic_str += "\nMean Tmax by farm:\n" + farm_means.round(2).to_string() + "\n"
            if "rainfall" in df.columns:
                analytic_str += f"\nOverall Rainfall Mean: {df['rainfall'].mean():.2f} mm, Std: {df['rainfall'].std():.2f}\n"
            if "cumulative_gdd" in df.columns:
                analytic_str += f"\nOverall GDD Mean: {df['cumulative_gdd'].mean():.2f}\n"
            # Show trend for top farm
            if "farm" in df.columns and "temp_max" in df.columns:
                farm_means = df.groupby("farm")["temp_max"].mean()
                analytic_str += "\nMean Tmax by farm:\n" + farm_means.round(2).to_string() + "\n"
                if "date" in df.columns:
                    top_farm = farm_means.idxmax()
                    df_top = df[df["farm"] == top_farm]
                    df_top["date"] = pd.to_datetime(df_top["date"])
                    df_top.sort_values("date", inplace=True)
                    df_top["temp_max_rm"] = df_top["temp_max"].rolling(window=3, min_periods=1).mean()
                    analytic_str += f"\nRolling mean for Tmax (farm={top_farm}):\n"
                    analytic_str += df_top[["date", "temp_max", "temp_max_rm"]].tail(5).to_string(index=False) + "\n"
            # Display
            top = tk.Toplevel(self)
            top.title("Global Analytics (Admin)")
            text = tk.Text(top, width=110, height=30, font=("Consolas", 10))
            text.pack(fill="both", expand=True)
            text.insert(tk.END, analytic_str or "No analytics available.")
            text.config(state="disabled")
        except Exception as e:
            messagebox.showerror("Global Analytics", f"Failed to compute analytics: {e}")

    def get_frame(self):
        return self

# --- Sample backend for cloud integration (Flask) ---
"""
# Save this as cloud_backend.py

from flask import Flask, request, jsonify
import os

app = Flask(__name__)
API_KEY = os.environ.get("REPORT_API_KEY", "changeme")
UPLOAD_DIR = "uploads"

@app.route('/report-upload', methods=['POST'])
def report_upload():
    auth = request.headers.get("Authorization", "")
    if not auth or not auth.startswith("Bearer ") or auth.split(" ",1)[1].strip() != API_KEY:
        return jsonify({"error": "Unauthorized"}), 401
    if 'file' not in request.files:
        return jsonify({"error": "No file uploaded"}), 400
    f = request.files['file']
    os.makedirs(UPLOAD_DIR, exist_ok=True)
    save_path = os.path.join(UPLOAD_DIR, f.filename)
    f.save(save_path)
    # Optional: store metadata like user, timestamp in a log/db
    return jsonify({"status": "success", "path": save_path}), 200

if __name__ == '__main__':
    app.run(debug=True, port=8080)
"""

