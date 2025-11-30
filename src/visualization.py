import tkinter as tk
import csv
import ttkbootstrap as tb
from tkinter import messagebox, filedialog, simpledialog
from db_handler import DBHandler
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import pandas as pd
import numpy as np
import os
from datetime import datetime
AUDIT_LOG_FILE = "visualization_audit_log.csv"


import tkinter as tk
from tkinter import ttk
import ttkbootstrap as tb
from tkinter import messagebox, filedialog, simpledialog
from db_handler import DBHandler
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import pandas as pd
import numpy as np
import os
from datetime import datetime

class VisualizationPage(tb.Frame):
    def safe_ui_update(self, func, *args, **kwargs):
        """Safely update UI from threads or after callbacks."""
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
    METRIC_CHOICES = [
        ("Max Temp", "temp_max"), ("Min Temp", "temp_min"),
        ("Rainfall", "rainfall"), ("Daily GDD", "daily_gdd"),
        ("Effective Rain", "effective_rainfall"), ("Cum GDD", "cumulative_gdd")
    ]
    PLOT_TYPES = ["Line", "Bar", "Scatter", "Histogram", "Boxplot", "Heatmap"]
    COLOR_THEMES = {
        "Default": {"primary": "#2563eb", "secondary": "#f3f4f6", "trend": "#10b981"},
        "Warm":    {"primary": "#fb5607", "secondary": "#ffbe0b", "trend": "#ff006e"},
        "Cool":    {"primary": "#06b6d4", "secondary": "#64748b", "trend": "#3b82f6"},
        "Dark":    {"primary": "#18181b", "secondary": "#27272a", "trend": "#facc15"},
    }

    def __init__(self, parent, user=None):
        super().__init__(parent)
        self.parent = parent
        self.user = user or {"username": "Guest", "role": "user"}
        self._shutdown = False

        # Modern tabbed interface
        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill="both", expand=True, padx=12, pady=10)

        # --- Plot Tab ---
        self.plot_tab = tb.Frame(self.notebook)
        self.notebook.add(self.plot_tab, text="Plot")

        # --- Data Table Tab ---
        self.data_tab = tb.Frame(self.notebook)
        self.notebook.add(self.data_tab, text="Data Table")

        # --- Animation Tab ---
        self.anim_tab = tb.Frame(self.notebook)
        self.notebook.add(self.anim_tab, text="Animation")

        # --- Controls (top of plot tab) ---
        controls = tb.Frame(self.plot_tab)
        controls.pack(fill="x", pady=6)
        tb.Label(controls, text="Farm:").pack(side="left", padx=2)
        self.farm_combo = tb.Combobox(controls, width=24, state="readonly")
        self.farm_combo.pack(side="left", padx=6)
        tb.Label(controls, text="Metric:").pack(side="left", padx=2)
        self.metric_var = tk.StringVar(value=self.METRIC_CHOICES[0][1])
        self.metric_combo = tb.Combobox(controls, values=[m[0] for m in self.METRIC_CHOICES], textvariable=self.metric_var, state="readonly", width=16)
        self.metric_combo.pack(side="left", padx=6)
        tb.Label(controls, text="Plot Type:").pack(side="left", padx=2)
        self.plot_type_var = tk.StringVar(value=self.PLOT_TYPES[0])
        self.plot_type_combo = tb.Combobox(controls, values=self.PLOT_TYPES, textvariable=self.plot_type_var, state="readonly", width=14)
        self.plot_type_combo.pack(side="left", padx=6)
        tb.Label(controls, text="Theme:").pack(side="left", padx=2)
        self.theme_var = tk.StringVar(value="Default")
        self.theme_combo = tb.Combobox(controls, values=list(self.COLOR_THEMES.keys()), textvariable=self.theme_var, state="readonly", width=12)
        self.theme_combo.pack(side="left", padx=6)

        # Date range
        tb.Label(controls, text="Start Date:").pack(side="left", padx=2)
        self.start_date_var = tk.StringVar()
        self.start_date_entry = tb.Entry(controls, textvariable=self.start_date_var, width=12)
        self.start_date_entry.pack(side="left", padx=2)
        tb.Label(controls, text="End Date:").pack(side="left", padx=2)
        self.end_date_var = tk.StringVar()
        self.end_date_entry = tb.Entry(controls, textvariable=self.end_date_var, width=12)
        self.end_date_entry.pack(side="left", padx=2)

        # Overlay/trendline
        self.overlay_var = tk.BooleanVar(value=False)
        tb.Checkbutton(controls, text="Overlay Metric", variable=self.overlay_var).pack(side="left", padx=6)
        self.overlay_metric = tk.StringVar(value=self.METRIC_CHOICES[1][1])
        self.overlay_combo = tb.Combobox(controls, values=[m[0] for m in self.METRIC_CHOICES], textvariable=self.overlay_metric, state="readonly", width=16)
        self.overlay_combo.pack(side="left", padx=2)
        self.trendline_var = tk.BooleanVar(value=False)
        tb.Checkbutton(controls, text="Show Trendline", variable=self.trendline_var).pack(side="left", padx=6)

        # Action buttons
        actions = tb.Frame(self.plot_tab)
        actions.pack(fill="x", pady=6)
        tb.Button(actions, text="Plot", width=12, command=self.plot).pack(side="left", padx=4)
        tb.Button(actions, text="Import CSV/Excel", width=18, command=self.import_data_dialog).pack(side="left", padx=4)
        tb.Button(actions, text="Export CSV", width=14, command=self.export_csv).pack(side="left", padx=4)
        tb.Button(actions, text="Export Image", width=14, command=self.export_image).pack(side="left", padx=4)
        tb.Button(actions, text="Show Audit History", width=18, command=self.show_audit_history).pack(side="left", padx=4)
        tb.Button(actions, text="Reset Form", width=12, command=self._reset_form).pack(side="left", padx=4)

        # Tooltip initialization
        self.tooltip = None

        # Progressbar for loading/plotting
        self.progress = ttk.Progressbar(self.plot_tab, mode="indeterminate", length=220)
        self.progress.pack(pady=6)

        # Matplotlib plot area
        self.fig = None
        self.ax = None
        self.canvas = None
        self._initialized = False
        self._plot_after_id = None

        # Data table (ttk.Treeview)
        self.tree = ttk.Treeview(self.data_tab, columns=[], show="headings")
        self.tree.pack(fill="both", expand=True, padx=12, pady=8)

        # Animation tab: loading spinner
        self.anim_canvas = tk.Canvas(self.anim_tab, width=120, height=120, bg="#f5f5f5", highlightthickness=0)
        self.anim_canvas.pack(pady=32)
        self._spinner_angle = 0
        self._spinner_id = None
        self._animate_spinner()

        # Notes
        notes_frame = tb.Frame(self.plot_tab)
        notes_frame.pack(anchor="w", pady=(0,10))
        tb.Label(notes_frame, text="Notes/Comments:").pack(side="left")
        self.notes_var = tk.StringVar()
        notes_entry = tb.Entry(notes_frame, textvariable=self.notes_var, width=44)
        notes_entry.pack(side="left", padx=8)

        # Data cache & audit
        self.df = pd.DataFrame()
        self.audit_trail = []
        self.farm_ids = []
        self.selected_farm_id = None
        self.farm_combo.bind("<<ComboboxSelected>>", self.on_farm_selected)
        self.load_persistent_audit_trail()

        # Bind controls for auto-plot
        self.metric_combo.bind("<<ComboboxSelected>>", lambda e: self.schedule_plot())
        self.plot_type_combo.bind("<<ComboboxSelected>>", lambda e: self.schedule_plot())
        self.overlay_combo.bind("<<ComboboxSelected>>", lambda e: self.schedule_plot())
        self.theme_combo.bind("<<ComboboxSelected>>", lambda e: self.schedule_plot())
        self.overlay_var.trace_add("write", lambda *a: self.schedule_plot())
        self.trendline_var.trace_add("write", lambda *a: self.schedule_plot())

    def _animate_spinner(self):
        self.anim_canvas.delete("spinner")
        x, y, r = 60, 60, 40
        angle = self._spinner_angle
        for i in range(12):
            a = (angle + i * 30) % 360
            rad = np.deg2rad(a)
            x0 = x + r * np.cos(rad)
            y0 = y + r * np.sin(rad)
            color = f"#2563eb" if i == 0 else f"#b3c6e7"
            self.anim_canvas.create_oval(x0-6, y0-6, x0+6, y0+6, fill=color, outline="", tags="spinner")
        self._spinner_angle = (self._spinner_angle + 30) % 360
        self._spinner_id = self.anim_canvas.after(100, self._animate_spinner)

    # first on_show block removed (duplicate). See the real on_show later in the file.

    def _add_tooltip(self, widget, text):
        def on_enter(event):
            def show_tooltip():
                if self.winfo_exists() and not self._shutdown:
                    self.tooltip = tk.Toplevel(widget)
                    self.tooltip.wm_overrideredirect(True)
                    x = widget.winfo_rootx() + 20
                    y = widget.winfo_rooty() + 20
                    self.tooltip.wm_geometry(f"+{x}+{y}")
                    label = tk.Label(self.tooltip, text=text, background="#ffffe0", relief="solid", borderwidth=1, font=("Segoe UI", 9))
                    label.pack(ipadx=4, ipady=2)
            self.safe_ui_update(show_tooltip)
        def on_leave(event):
            def hide_tooltip():
                if hasattr(self, 'tooltip') and self.tooltip:
                    self.tooltip.destroy()
                    self.tooltip = None
            self.safe_ui_update(hide_tooltip)
        widget.bind("<Enter>", on_enter)
        widget.bind("<Leave>", on_leave)

    def schedule_plot(self, delay_ms: int = 300):
        """Schedule a debounced plot call. Cancels the previous pending one."""
        try:
            # cancel previous
            _pid = getattr(self, '_plot_after_id', None)
            if _pid is not None:
                try:
                    self.after_cancel(_pid)
                except Exception:
                    pass
            # schedule new
            try:
                self._plot_after_id = self.after(delay_ms, lambda: self.safe_ui_update(self.plot))
            except Exception:
                # fallback immediate
                try:
                    self.safe_ui_update(self.plot)
                except Exception:
                    pass
        except Exception:
            pass

    def on_show(self):
        """Lazily initialize heavy widgets (matplotlib canvas) and load farms when the page becomes visible."""
        if getattr(self, '_initialized', False):
            return
        try:
            # create matplotlib figure and canvas lazily
            # create figure without constrained_layout to avoid collapsed axes warning on some backends
            self.fig, self.ax = plt.subplots(figsize=(7.5, 4.5))
            self.canvas = FigureCanvasTkAgg(self.fig, master=self.plot_tab)
            canvas_widget = self.canvas.get_tk_widget()
            canvas_widget.config(width=640, height=380)
            canvas_widget.pack(pady=12, fill="both", expand=True)
            # after the canvas widget is available, call tight_layout to arrange axes
            try:
                self.fig.tight_layout()
            except Exception:
                pass

            # load farms (this will also optionally call plot if farms exist)
            self.load_farms()
            # If farms were loaded, trigger an initial plot automatically
            try:
                if getattr(self, 'farm_ids', None):
                    # schedule plot on the mainloop to avoid nested UI work during on_show
                    try:
                        self.safe_ui_update(self.plot)
                    except Exception:
                        # fallback: direct call
                        try:
                            self.plot()
                        except Exception:
                            pass
            except Exception:
                pass
            self._initialized = True
        except Exception:
            # If something goes wrong during lazy init, ignore to avoid crashing the UI
            pass

    def _reset_form(self):
        self.farm_combo.set("")
        self.metric_var.set(self.METRIC_CHOICES[0][1])
        self.plot_type_var.set("line")
        self.theme_var.set("Default")
        self.start_date_var.set("")
        self.end_date_var.set("")
        self.overlay_var.set(False)
        self.overlay_metric.set(self.METRIC_CHOICES[1][1])
        self.trendline_var.set(False)
        self.notes_var.set("")

    def export_image(self):
        if not self.df.empty:
            file_path = filedialog.asksaveasfilename(
                title="Export Plot as Image",
                defaultextension=".png",
                filetypes=[("PNG Image", "*.png"), ("All Files", "*.*")]
            )
            if not file_path:
                return
            try:
                # ensure figure exists (lazy init)
                if getattr(self, '_initialized', False) and self.fig is not None:
                    self.fig.savefig(file_path)
                else:
                    # attempt to initialize the view and then save
                    try:
                        self.on_show()
                    except Exception:
                        pass
                    if self.fig is not None:
                        self.fig.savefig(file_path)
                    else:
                        raise RuntimeError("Figure not initialized")
                self._audit("image_export", f"Plot image exported by {self.user.get('username') }.")
                messagebox.showinfo("Export", f"Image exported to {file_path}")
            except Exception as e:
                messagebox.showerror("Export Error", f"Failed to export image: {e}")

    def cloud_export_stub(self):
        if not self.df.empty:
            file_path = filedialog.asksaveasfilename(
                title="Export Plot to Cloud (stub)",
                defaultextension=".png",
                filetypes=[("PNG Image", "*.png"), ("All Files", "*.*")]
            )
            if not file_path:
                return
            try:
                if getattr(self, '_initialized', False) and self.fig is not None:
                    self.fig.savefig(file_path)
                else:
                    try:
                        self.on_show()
                    except Exception:
                        pass
                    if self.fig is not None:
                        self.fig.savefig(file_path)
                    else:
                        raise RuntimeError("Figure not initialized")
                self._audit("cloud_export", f"Plot image cloud-exported by {self.user.get('username') }.")
                messagebox.showinfo("Export", f"Image exported (stub) to cloud: {file_path}")
            except Exception as e:
                messagebox.showerror("Export Error", f"Failed to cloud export image: {e}")

    def collaborate_stub(self):
        room = simpledialog.askstring("Collaborate", "Enter room/session name to join or create:")
        if room:
            messagebox.showinfo("Collaboration", f"Collaboration session '{room}' (stub). Integrate with backend for real-time sync.")

    def _audit(self, action_type, msg):
        record = {
            "timestamp": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"),
            "user": self.user.get("username", "Guest"),
            "action": action_type,
            "message": msg
        }
        self.audit_trail.append(record)
        self.save_persistent_audit_trail()

    def show_audit_history(self):
        top = tk.Toplevel(self)
        top.title("Visualization Audit History")
        text = tk.Text(top, width=80, height=18, font=("Consolas", 10))
        text.pack(padx=10, pady=10)
        if self.audit_trail:
            for rec in self.audit_trail:
                text.insert("end", f"{rec['timestamp']} | {rec['user']} | {rec['action']} | {rec['message']}\n")
        else:
            text.insert("end", "No audit history found.")

    def plot(self):
        """Query DB for selected farm/date/metric and draw the plot on the canvas."""
        try:
            # Ensure the canvas/figure are initialized
            if not getattr(self, '_initialized', False):
                try:
                    self.on_show()
                except Exception:
                    pass

            # Determine metric key (support either label or key in the combobox)
            metric_val = self.metric_var.get()
            metric_key = None
            for lbl, key in self.METRIC_CHOICES:
                if metric_val == key or metric_val == lbl:
                    metric_key = key
                    break
            if metric_key is None:
                # fallback to first metric
                metric_key = self.METRIC_CHOICES[0][1]

            # overlay metric
            overlay_key = None
            if self.overlay_var.get():
                ov = self.overlay_metric.get()
                for lbl, key in self.METRIC_CHOICES:
                    if ov == key or ov == lbl:
                        overlay_key = key
                        break

            # Map metric keys to table columns (cloned from report_page style)
            field_map = {
                "date": "c.date",
                "temp_max": "c.temp_max",
                "temp_min": "c.temp_min",
                "rainfall": "c.rainfall",
                "daily_gdd": "m.daily_gdd",
                "effective_rainfall": "m.effective_rainfall",
                "cumulative_gdd": "m.cumulative_gdd"
            }

            date_col = "c.date"
            metric_col = field_map.get(metric_key, f"c.{metric_key}")
            overlay_col = field_map.get(overlay_key) if overlay_key else None

            # Get date range and farm
            farm_id = self.selected_farm_id
            if not farm_id:
                messagebox.showwarning("Plot", "Please select a farm to plot.")
                return
            start_date = self.start_date_var.get().strip()
            end_date = self.end_date_var.get().strip()

            # Build query
            select_clause = f"{date_col}, {metric_col}"
            if overlay_col:
                select_clause += f", {overlay_col}"
            q = f"SELECT {select_clause} FROM climate_data c LEFT JOIN agri_metrics m ON c.farm_id = m.farm_id AND c.date = m.date WHERE c.farm_id=?"
            params = [farm_id]
            if start_date:
                q += " AND c.date>=?"
                params.append(start_date)
            if end_date:
                q += " AND c.date<=?"
                params.append(end_date)
            q += " ORDER BY c.date ASC"

            with DBHandler() as db:
                rows = db.fetch_all(q, tuple(params))

            # Build DataFrame
            if not rows:
                # No data: clear axes and show message
                ax = getattr(self, 'ax', None)
                canvas = getattr(self, 'canvas', None)
                if ax is not None:
                    def _no_data(a=ax):
                        a.clear()
                        a.text(0.5, 0.5, "No data available for selection", ha="center", va="center", fontsize=12)
                    self.safe_ui_update(_no_data)
                if canvas is not None:
                    self.safe_ui_update(lambda c=canvas: c.draw())
                return

            # Convert rows to DataFrame
            cols = ["date", metric_key]
            if overlay_col and overlay_key:
                cols.append(overlay_key)
            df = pd.DataFrame(rows, columns=cols)
            # parse dates
            try:
                df["date"] = pd.to_datetime(df["date"])
            except Exception:
                pass
            self.df = df

            # Plot on axes
            ax = getattr(self, 'ax', None)
            canvas = getattr(self, 'canvas', None)
            if ax is None or canvas is None:
                return

            def _draw(a=ax, data=df):
                try:
                    a.clear()
                    plot_type = self.plot_type_var.get()
                    x = data["date"]
                    y = data[metric_key]
                    if plot_type == "line":
                        a.plot(x, y, marker="o", label=metric_key)
                    elif plot_type == "bar":
                        a.bar(x, y, label=metric_key)
                    elif plot_type == "scatter":
                        a.scatter(x, y, label=metric_key)
                    elif plot_type == "histogram":
                        a.hist(y.dropna(), bins=10)
                    elif plot_type == "boxplot":
                        a.boxplot(y.dropna())
                    else:
                        # fallback to line for unknown types
                        a.plot(x, y, marker="o", label=metric_key)

                    # overlay
                    if overlay_col and overlay_key in data.columns:
                        try:
                            ov_y = data[overlay_key]
                            a.plot(x, ov_y, marker="x", linestyle="--", label=overlay_key)
                        except Exception:
                            pass

                    if self.trendline_var.get() and len(data) >= 2:
                        try:
                            # simple linear trend
                            xv = np.arange(len(x))
                            valid = ~np.isnan(y)
                            if valid.sum() >= 2:
                                coeffs = np.polyfit(xv[valid], y[valid].astype(float), 1)
                                trend = np.polyval(coeffs, xv)
                                a.plot(x, trend, color="#ff6600", linewidth=1.6, label="Trendline")
                        except Exception:
                            pass

                    a.set_title(f"{metric_key} for farm {self.selected_farm_id}")
                    a.set_xlabel("Date")
                    a.set_ylabel(metric_key)
                    try:
                        a.legend()
                    except Exception:
                        pass
                except Exception:
                    pass

            self.safe_ui_update(_draw)
            # format dates and draw
            try:
                fig = getattr(self, 'fig', None)
                if fig is not None:
                    # capture fig locally to avoid static analyzer thinking self.fig may be None
                    self.safe_ui_update(lambda f=fig: f.autofmt_xdate(rotation=25))
            except Exception:
                pass
            self.safe_ui_update(lambda c=canvas: c.draw())
            # audit
            try:
                self._audit("plot", f"Plotted {metric_key} for farm {self.selected_farm_id}")
            except Exception:
                pass
        except Exception:
            pass

    def export_csv(self):
        """Export the currently plotted DataFrame to CSV."""
        try:
            if getattr(self, 'df', None) is None or self.df.empty:
                messagebox.showwarning("Export", "No plotted data to export.")
                return
            file_path = filedialog.asksaveasfilename(
                title="Export Data as CSV",
                defaultextension=".csv",
                filetypes=[("CSV Files", "*.csv"), ("All Files", "*.*")]
            )
            if not file_path:
                return
            try:
                self.df.to_csv(file_path, index=False)
                self._audit("export_csv", f"Exported plotted data to {file_path}")
                messagebox.showinfo("Export", f"Data exported to {file_path}")
            except Exception as e:
                messagebox.showerror("Export Error", f"Failed to export CSV: {e}")
        except Exception:
            pass

    def refresh_after_import(self):
        # Reload farm list and optionally refresh data/plots after import
        self.load_farms()
        # Optionally refresh data/plots after import
        self.plot()  # Automatically refresh plot after import

    def import_data_dialog(self):
        """Dialog to select and import CSV/Excel into DB."""
        file_path = filedialog.askopenfilename(
            title="Select CSV or Excel File",
            filetypes=[("CSV/Excel Files", "*.csv;*.xls;*.xlsx"), ("All Files", "*.*")]
        )
        if not file_path:
            return
        # Ask for farm_id if not set
        farm_id = self.selected_farm_id
        if not farm_id:
            farm_id = simpledialog.askstring("Farm ID", "Enter Farm ID for import:")
            if not farm_id:
                messagebox.showwarning("Import", "No farm ID provided.")
                return
        try:
            from import_utils import import_file_to_db
            inserted = import_file_to_db(file_path, farm_id)
            messagebox.showinfo("Import", f"Imported {inserted} rows from {os.path.basename(file_path)}.")
            self.refresh_after_import()
        except Exception as e:
            messagebox.showerror("Import Error", str(e))

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

    def on_farm_selected(self, event=None):
        idx = self.farm_combo.current()
        if idx < 0 or idx >= len(self.farm_ids):
            self.selected_farm_id = None
        else:
            self.selected_farm_id = self.farm_ids[idx]

    def save_persistent_audit_trail(self):
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
