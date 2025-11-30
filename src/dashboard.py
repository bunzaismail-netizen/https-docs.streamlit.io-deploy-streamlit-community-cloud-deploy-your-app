import hashlib
import ttkbootstrap as tb
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import tkinter as tk
from tkinter import messagebox, filedialog, simpledialog, ttk
import csv
import threading
import os
from db_handler import DBHandler
from featured_media import FeaturedMediaFrame

THEMES = ["cyborg", "minty", "solar", "morph", "pulse", "flatly", "superhero", "darkly", "cosmo", "journal", "litera", "sandstone", "yeti"]

class Dashboard(tb.Frame):
    def __init__(self, parent):
        super().__init__(parent)
        self.parent = parent
        self.style = tb.Style()
        self.temp_alert_threshold = 35.0
        self.rain_alert_threshold = 5.0

        # Main content area only
        main = tb.Frame(self)
        main.pack(fill="both", expand=True, padx=12, pady=8)

        # Date range filter
        date_filter_frame = tb.Frame(main)
        date_filter_frame.pack(pady=(0,8))
        tb.Label(date_filter_frame, text="Start Date:", font=("Segoe UI", 10)).pack(side="left")
        self.start_date_entry = tb.Entry(date_filter_frame, width=12)
        self.start_date_entry.pack(side="left", padx=5)
        tb.Label(date_filter_frame, text="End Date:", font=("Segoe UI", 10)).pack(side="left")
        self.end_date_entry = tb.Entry(date_filter_frame, width=12)
        self.end_date_entry.pack(side="left", padx=5)
        tb.Button(date_filter_frame, text="Apply Filter", command=self.apply_date_filter).pack(side="left", padx=10)

        # Top Action Buttons
        self.action_btn_frame = tb.Frame(main)
        self.action_btn_frame.pack(pady=(0, 16), anchor="w")
        tb.Button(self.action_btn_frame, text="➕ Add Farm/Data", width=17, command=self.add_entry, style="success.Outline.TButton").pack(side="left", padx=7)
        tb.Button(self.action_btn_frame, text="✏ Edit Selected", width=17, command=self.edit_entry, style="warning.Outline.TButton").pack(side="left", padx=7)
        tb.Button(self.action_btn_frame, text="🗑 Delete Selected", width=17, command=self.delete_entry, style="danger.Outline.TButton").pack(side="left", padx=7)

        # Other Buttons row
        self.btn_frame = tb.Frame(main)
        self.btn_frame.pack(pady=10)
        tb.Button(self.btn_frame, text="🔄 Refresh Data", width=17, command=self.refresh_data, style="info.Outline.TButton").grid(row=0, column=0, padx=7)
        tb.Button(self.btn_frame, text="💾 Export PNG", width=17, command=self.export_report).grid(row=0, column=1, padx=7)
        tb.Button(self.btn_frame, text="⬇ Export CSV", width=17, command=self.export_csv).grid(row=0, column=2, padx=7)
        tb.Button(self.btn_frame, text="📄 Export PDF", width=17, command=self.export_pdf).grid(row=0, column=3, padx=7)
        tb.Button(self.btn_frame, text="⚠ Alerts", width=17, command=self.show_alerts).grid(row=0, column=4, padx=7)
        tb.Button(self.btn_frame, text="📤 Upload CSV", width=17, command=self.upload_csv).grid(row=0, column=5, padx=7)
        tb.Button(self.btn_frame, text="📥 Load Sample Data", width=17, command=self.load_sample_data).grid(row=0, column=6, padx=7)
        tb.Button(self.btn_frame, text="⬇ Download CSV Template", width=17, command=self.download_csv_template).grid(row=0, column=7, padx=7)

        # Info label
        self.info_label = tb.Label(main, text="", font=("Segoe UI", 10, "italic"))
        self.info_label.pack(pady=(0, 8))

        # Featured Image/Video Section
        self.featured_media = FeaturedMediaFrame(main, image_path="featured.jpg")
        self.featured_media.pack(pady=(0, 8))

        # Summary cards
        summary_frame = tb.Frame(main)
        summary_frame.pack(pady=(0, 8), fill="x")
        card_style = {"font":("Segoe UI", 13, "bold"), "background":"#f7f7f7", "foreground":"#222", "padding":10, "borderwidth":2, "relief":"groove"}
        self.avg_temp_label = tb.Label(summary_frame, text="Avg Temp: --", **card_style)
        self.avg_temp_label.pack(side="left", padx=10, ipadx=10, ipady=10)
        self.total_rain_label = tb.Label(summary_frame, text="Total Rainfall: --", **card_style)
        self.total_rain_label.pack(side="left", padx=10, ipadx=10, ipady=10)
        self.gdd_label = tb.Label(summary_frame, text="Cum. GDD: --", **card_style)
        self.gdd_label.pack(side="left", padx=10, ipadx=10, ipady=10)
        self.min_temp_label = tb.Label(summary_frame, text="Min Temp: --", **card_style)
        self.min_temp_label.pack(side="left", padx=10, ipadx=10, ipady=10)
        self.max_temp_label = tb.Label(summary_frame, text="Max Temp: --", **card_style)
        self.max_temp_label.pack(side="left", padx=10, ipadx=10, ipady=10)

        # Chart area (temp + metrics) - defer heavy creation until shown
        chart_frame = tb.Frame(main, style="info.TFrame", padding=10, borderwidth=2, relief="ridge")
        chart_frame.pack(pady=8, fill="both", expand=True)
        self._chart_parent = chart_frame
        self.fig = None
        self.ax_temp = None
        self.ax_gdd = None
        self.canvas = None
        self._initialized = False
        self._shutdown = False

        # Metrics table
        table_frame = tb.Frame(main, padding=10)
        table_frame.pack(pady=8, fill="x", expand=True)
        self.table = ttk.Treeview(table_frame, columns=("date", "temp_max", "temp_min", "rain", "daily_gdd", "eff_rain", "cum_gdd"), show="headings", height=7)
        for col, lbl in zip(self.table["columns"], ["Date", "Max T", "Min T", "Rain", "Daily GDD", "Eff Rain", "Cum GDD"]):
            self.table.heading(col, text=lbl)
        self.table.tag_configure('oddrow', background='#f0f0f0')
        self.table.tag_configure('evenrow', background='#e0e0e0')
        self.table.pack(fill="x", expand=True)

        # Theme selection combobox
        theme_frame = tb.Frame(main)
        theme_frame.pack(pady=(0, 8))
        tb.Label(theme_frame, text="Theme:", font=("Segoe UI", 10)).pack(side="left")
        self.theme_name = tk.StringVar(value=THEMES[0])
        self.theme_combo = ttk.Combobox(theme_frame, textvariable=self.theme_name, values=THEMES, state="readonly", width=18)
        self.theme_combo.pack(side="left", padx=5)
        self.theme_combo.bind("<<ComboboxSelected>>", self.switch_theme)

        # Farm selection combobox
        farm_select_frame = tb.Frame(main)
        farm_select_frame.pack(pady=(0, 8))
        tb.Label(farm_select_frame, text="Select Farm:", font=("Segoe UI", 10)).pack(side="left")
        self.farm_combo = ttk.Combobox(farm_select_frame, state="readonly", width=24)
        self.farm_combo.pack(side="left", padx=5)

    # farm list and imports will be handled when page is actually shown (on_show)

    def on_show(self):
        """Lazily initialize chart, load farms, and import template when the dashboard becomes visible."""
        if getattr(self, '_initialized', False):
            return
        try:
            # create matplotlib figure and canvas lazily
            # create figure without constrained_layout to avoid collapsed axes warning
            self.fig, (self.ax_temp, self.ax_gdd) = plt.subplots(2, 1, figsize=(7, 7))
            self.canvas = FigureCanvasTkAgg(self.fig, master=self._chart_parent)
            self.canvas.draw()
            self.canvas.get_tk_widget().pack(fill="both", expand=True)
            try:
                self.fig.tight_layout()
            except Exception:
                pass
            self._initialized = True
        except Exception:
            pass

        # Start background worker to import template (if present) and load farms
        def worker():
            try:
                template_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "climate_template_2025.csv")
                if os.path.exists(template_path):
                    try:
                        with open(template_path, "r", newline="") as f:
                            reader = csv.DictReader(f)
                            with DBHandler() as db:
                                db.execute_query("INSERT OR IGNORE INTO farms (name, location, base_temp) VALUES (?, ?, ?)", ("Template Farm", "Unknown", 10.0))
                                farm_row = db.fetch_one("SELECT id FROM farms WHERE name=?", ("Template Farm",))
                                if farm_row:
                                    farm_id = farm_row[0]
                                    for row in reader:
                                        try:
                                            db.execute_query(
                                                "INSERT OR REPLACE INTO climate_data (farm_id, date, temp_max, temp_min, rainfall) VALUES (?, ?, ?, ?, ?)",
                                                (farm_id, row.get("date"), float(row.get("temp_max") or 0), float(row.get("temp_min") or 0), float(row.get("rainfall") or 0))
                                            )
                                            db.execute_query(
                                                "INSERT OR REPLACE INTO agri_metrics (farm_id, date, daily_gdd, effective_rainfall, cumulative_gdd) VALUES (?, ?, ?, ?, ?)",
                                                (farm_id, row.get("date"), float(row.get("daily_gdd") or 0), float(row.get("eff_rain") or 0), float(row.get("cum_gdd") or 0))
                                            )
                                        except Exception:
                                            continue
                    except Exception:
                        pass

                # fetch farms list
                with DBHandler() as db:
                    farms = db.fetch_all("SELECT id, name FROM farms ORDER BY name")

                def finish_ui():
                    try:
                        if farms:
                            self.farms = farms
                            farm_names = [f[1] for f in farms]
                            self.farm_combo["values"] = farm_names
                            self.farm_combo.current(0)
                            self.selected_farm_id = farms[0][0]
                            self.update_farm_info()
                            self.update_chart()
                        else:
                            self.farm_combo["values"] = []
                            self.info_label.config(text="No farms in database.")
                            self.selected_farm_id = None
                            if hasattr(self, 'table') and self.table is not None:
                                for row in self.table.get_children():
                                    self.table.delete(row)
                            self.update_chart()
                    except Exception:
                        pass

                self.safe_ui_update(finish_ui)
            except Exception:
                pass

        threading.Thread(target=worker, daemon=True).start()

    def auto_import_climate_template(self):
        """Force import of climate_template_2025.csv into a farm named 'Template Farm', and select it as default."""
        import os
        template_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "climate_template_2025.csv")
        if not os.path.exists(template_path):
            return
        try:
            with open(template_path, "r", newline="") as f:
                reader = csv.DictReader(f)
                with DBHandler() as db:
                    # Always create/find 'Template Farm'
                    db.execute_query("INSERT OR IGNORE INTO farms (name, location, base_temp) VALUES (?, ?, ?)", ("Template Farm", "Unknown", 10.0))
                    farm_row = db.fetch_one("SELECT id FROM farms WHERE name=?", ("Template Farm",))
                    if not farm_row:
                        return
                    farm_id = farm_row[0]
                    for row in reader:
                        db.execute_query(
                            "INSERT OR REPLACE INTO climate_data (farm_id, date, temp_max, temp_min, rainfall) VALUES (?, ?, ?, ?, ?)",
                            (farm_id, row["date"], float(row["temp_max"]), float(row["temp_min"]), float(row["rainfall"]))
                        )
                        db.execute_query(
                            "INSERT OR REPLACE INTO agri_metrics (farm_id, date, daily_gdd, effective_rainfall, cumulative_gdd) VALUES (?, ?, ?, ?, ?)",
                            (farm_id, row["date"], float(row["daily_gdd"]), float(row["eff_rain"]), float(row["cum_gdd"]))
                        )
            # After import, set 'Template Farm' as selected
            self.load_farms()
            farm_names = [f[1] for f in self.farms]
            if "Template Farm" in farm_names:
                idx = farm_names.index("Template Farm")
                self.farm_combo.current(idx)
                self.selected_farm_id = self.farms[idx][0]
                self.update_farm_info()
                self.update_chart()
        except Exception:
            pass

    def safe_ui_update(self, func, *args, **kwargs):
        """Safely call UI-updating functions from background threads."""
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

    def destroy(self):
        # Mark for shutdown to prevent background threads from updating UI
        self._shutdown = True
        try:
            # remove canvas widget if present
            if hasattr(self, 'canvas') and self.canvas:
                try:
                    w = self.canvas.get_tk_widget()
                    if w:
                        w.destroy()
                except Exception:
                    pass
        except Exception:
            pass
        super().destroy()

    def logout(self):
        from tkinter import messagebox
        if messagebox.askyesno("Logout", "Are you sure you want to logout?"):
            self.parent.destroy()

    def upload_csv(self):
        from tkinter import filedialog, messagebox
        file_path = filedialog.askopenfilename(filetypes=[("CSV Files", "*.csv"), ("All Files", "*.*")])
        if not file_path:
            return
        try:
            with open(file_path, "r", newline="") as f:
                reader = csv.reader(f)
                headers = next(reader)
                # Expecting columns: Date, Temp Max, Temp Min, Rainfall, Daily GDD, Eff Rain, Cum GDD
                for row in reader:
                    if len(row) < 7:
                        continue
                    date, temp_max, temp_min, rainfall, daily_gdd, eff_rain, cum_gdd = row[:7]
                    # Insert into DB
                    with DBHandler() as db:
                        db.execute_query(
                            "INSERT OR IGNORE INTO climate_data (farm_id, date, temp_max, temp_min, rainfall) VALUES (?, ?, ?, ?, ?)",
                            (self.selected_farm_id, date, float(temp_max), float(temp_min), float(rainfall))
                        )
                        db.execute_query(
                            "INSERT OR IGNORE INTO agri_metrics (farm_id, date, daily_gdd, effective_rainfall, cumulative_gdd) VALUES (?, ?, ?, ?, ?)",
                            (self.selected_farm_id, date, float(daily_gdd), float(eff_rain), float(cum_gdd))
                        )
            self.refresh_data()
            messagebox.showinfo("Upload", f"CSV data imported from {file_path}")
        except Exception as e:
            messagebox.showerror("Upload Error", f"Failed to import CSV: {e}")

        # --- Load farms and data ---
        self.load_farms()

    def load_sample_data(self):
        """Load sample data from sample_climate_data.csv into the database."""
        import os
        sample_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "sample_climate_data.csv")
        if not os.path.exists(sample_path):
            messagebox.showerror("Sample Data", f"File not found: {sample_path}")
            return
        try:
            with open(sample_path, "r", newline="") as f:
                reader = csv.DictReader(f)
                # Use first farm or create a default farm
                with DBHandler() as db:
                    farms = db.fetch_all("SELECT id FROM farms LIMIT 1")
                    if farms:
                        farm_id = farms[0][0]
                    else:
                        db.execute_query("INSERT INTO farms (name, location, base_temp) VALUES (?, ?, ?)", ("Sample Farm", "Unknown", 10.0))
                        farm_row = db.fetch_one("SELECT id FROM farms WHERE name=?", ("Sample Farm",))
                        if farm_row:
                            farm_id = farm_row[0]
                        else:
                            messagebox.showerror("Sample Data Error", "Could not create or find Sample Farm in database.")
                            return
                    for row in reader:
                        db.execute_query(
                            "INSERT OR IGNORE INTO climate_data (farm_id, date, temp_max, temp_min, rainfall) VALUES (?, ?, ?, ?, ?)",
                            (farm_id, row["date"], float(row["temp_max"]), float(row["temp_min"]), float(row["rainfall"]))
                        )
                        db.execute_query(
                            "INSERT OR IGNORE INTO agri_metrics (farm_id, date, daily_gdd, effective_rainfall, cumulative_gdd) VALUES (?, ?, ?, ?, ?)",
                            (farm_id, row["date"], float(row["daily_gdd"]), float(row["eff_rain"]), float(row["cum_gdd"]))
                        )
            self.refresh_data()
            messagebox.showinfo("Sample Data", "Sample climate data loaded successfully.")
        except Exception as e:
            messagebox.showerror("Sample Data Error", f"Failed to load sample data: {e}")

    # ----- Theme Switch -----
    def switch_theme(self, event=None):
        th = self.theme_name.get()
        self.style.theme_use(th)

    # ----- Data Loaders -----
    def load_farms(self):
        with DBHandler() as db:
            self.farms = db.fetch_all("SELECT id, name FROM farms ORDER BY name")
        if self.farms:
            farm_names = [f[1] for f in self.farms]
            self.farm_combo["values"] = farm_names
            # Do not create heavy matplotlib objects here; on_show handles chart initialization.
            # Clear table rows if present
            if hasattr(self, 'table') and self.table is not None:
                for row in self.table.get_children():
                    try:
                        self.table.delete(row)
                    except Exception:
                        pass

        # Note: template import and farms loading is handled by on_show() background worker to avoid duplicate work.

    def update_farm_info(self):
        with DBHandler() as db:
            farm = db.fetch_one("SELECT name, location, base_temp FROM farms WHERE id=?", (self.selected_farm_id,))
            if farm:
                name, loc, base = farm
                self.info_label.config(text=f"{name} | Location: {loc} | Base Temp: {base} °C")
            else:
                self.info_label.config(text="Farm info not found.")

    def get_trends(self, start_date=None, end_date=None):
        if not self.selected_farm_id:
            return [], [], [], [], [], [], []
        query = """
            SELECT c.date, c.temp_max, c.temp_min, c.rainfall,
                   m.daily_gdd, m.effective_rainfall, m.cumulative_gdd
            FROM climate_data c
            LEFT JOIN agri_metrics m ON c.farm_id = m.farm_id AND c.date = m.date
            WHERE c.farm_id=?
        """
        params = [self.selected_farm_id]
        if start_date:
            query += " AND c.date >= ?"
            params.append(start_date)
        if end_date:
            query += " AND c.date <= ?"
            params.append(end_date)
        query += " ORDER BY c.date ASC"
        with DBHandler() as db:
            cursor = db.execute_query(query, tuple(params))
            rows = cursor.fetchall() if cursor else []
        dates, temp_max, temp_min, rain, daily_gdd, eff_rain, cum_gdd = [], [], [], [], [], [], []
        for row in rows:
            dates.append(row[0])
            temp_max.append(row[1])
            temp_min.append(row[2])
            rain.append(row[3])
            daily_gdd.append(row[4])
            eff_rain.append(row[5])
            cum_gdd.append(row[6])
        return dates, temp_max, temp_min, rain, daily_gdd, eff_rain, cum_gdd

    # ----- Chart/Table/Stats Update -----
    def update_chart(self, start_date=None, end_date=None):
        # Ensure chart widgets exist
        if not getattr(self, '_initialized', False):
            try:
                self.on_show()
            except Exception:
                pass

        dates, temp_max, temp_min, rain, daily_gdd, eff_rain, cum_gdd = self.get_trends(start_date, end_date)
        # If axes are still not created, skip updating chart
        if self.ax_temp is None or self.ax_gdd is None:
            return
        self.ax_temp.clear()
        self.ax_gdd.clear()
        # Table
        for row in self.table.get_children():
            self.table.delete(row)
        # Summary stats
        if dates:
            self.ax_temp.plot(dates, temp_max, marker="o", color="#0d6efd", label="Max Temp")
            self.ax_temp.plot(dates, temp_min, marker="s", color="#33aa33", label="Min Temp")
            self.ax_temp.set_title("Temperature Trend")
            self.ax_temp.set_xlabel("Date")
            self.ax_temp.set_ylabel("Temperature (°C)")
            self.ax_temp.legend()
            self.ax_gdd.plot(dates, daily_gdd, marker="s", color="orange", label="Daily GDD")
            self.ax_gdd.plot(dates, eff_rain, marker="^", color="green", label="Eff. Rainfall")
            self.ax_gdd.plot(dates, cum_gdd, marker="D", color="purple", label="Cumulative GDD")
            self.ax_gdd.set_title("Agri Metrics Trend")
            self.ax_gdd.set_xlabel("Date")
            self.ax_gdd.set_ylabel("Value")
            self.ax_gdd.legend()
            # Fill table
            for row in zip(dates, temp_max, temp_min, rain, daily_gdd, eff_rain, cum_gdd):
                self.table.insert('', 'end', values=[*row])
            # Cards
            temp_vals = [t for t in temp_max if t is not None]
            min_vals = [t for t in temp_min if t is not None]
            rain_vals = [r for r in rain if r is not None]
            gdd_vals = [g for g in cum_gdd if g is not None]
            self.avg_temp_label.config(text=f"Avg Temp: {sum(temp_vals)/len(temp_vals):.1f}°C" if temp_vals else "Avg Temp: --")
            self.total_rain_label.config(text=f"Total Rain: {sum(rain_vals):.1f}mm" if rain_vals else "Total Rain: --")
            self.gdd_label.config(text=f"Cum. GDD: {gdd_vals[-1]:.1f}" if gdd_vals else "Cum. GDD: --")
            self.min_temp_label.config(text=f"Min T: {min(min_vals):.1f}°C" if min_vals else "Min T: --")
            self.max_temp_label.config(text=f"Max T: {max(temp_vals):.1f}°C" if temp_vals else "Max T: --")
        else:
            if self.ax_temp is not None:
                self.ax_temp.text(0.5, 0.5, "No data available", ha="center", va="center", fontsize=12)
                self.ax_temp.set_xticks([])
                self.ax_temp.set_yticks([])
                self.ax_temp.set_title("Temperature Trend")
            if self.ax_gdd is not None:
                self.ax_gdd.text(0.5, 0.5, "No data available", ha="center", va="center", fontsize=12)
                self.ax_gdd.set_xticks([])
                self.ax_gdd.set_yticks([])
                self.ax_gdd.set_title("Agri Metrics Trend")
            self.avg_temp_label.config(text="Avg Temp: --")
            self.total_rain_label.config(text="Total Rain: --")
            self.gdd_label.config(text="Cum. GDD: --")
            self.min_temp_label.config(text="Min Temp: --")
            self.max_temp_label.config(text="Max Temp: --")
        try:
            if self.canvas:
                self.canvas.draw()
        except Exception:
            pass

    def refresh_data(self):
        self.load_farms()
        if self.winfo_exists():
            messagebox.showinfo("Info", "Data has been refreshed.")

    # ----- Export Features -----
    def export_report(self):
        file_path = filedialog.asksaveasfilename(defaultextension=".png", filetypes=[("PNG Files", "*.png"), ("All Files", "*.*")])
        if file_path:
            try:
                if not getattr(self, '_initialized', False):
                    self.on_show()
            except Exception:
                pass
            if self.fig:
                self.fig.savefig(file_path)
            messagebox.showinfo("Export", f"Chart exported to:\n{file_path}")

    def export_csv(self):
        file_path = filedialog.asksaveasfilename(defaultextension=".csv", filetypes=[("CSV Files", "*.csv"), ("All Files", "*.*")])
        if file_path:
            with open(file_path, "w", newline="") as f:
                writer = csv.writer(f)
                writer.writerow(["Date", "Temp Max", "Temp Min", "Rainfall", "Daily GDD", "Eff Rain", "Cum GDD"])
                for row in self.table.get_children():
                    writer.writerow(self.table.item(row)["values"])
            messagebox.showinfo("Export", f"Table exported to:\n{file_path}")

    def export_pdf(self):
        try:
            from matplotlib.backends.backend_pdf import PdfPages
        except ImportError:
            messagebox.showerror("Export PDF", "matplotlib.backends.backend_pdf not available.")
            return
        file_path = filedialog.asksaveasfilename(defaultextension=".pdf", filetypes=[("PDF Files", "*.pdf"), ("All Files", "*.*")])
        if file_path:
            try:
                if not getattr(self, '_initialized', False):
                    self.on_show()
            except Exception:
                pass
            if self.fig:
                with PdfPages(file_path) as pdf:
                    pdf.savefig(self.fig)
            messagebox.showinfo("Export", f"Chart PDF exported to:\n{file_path}")

    # ----- Alerts -----
    def show_alerts(self):
        if not self.selected_farm_id:
            messagebox.showwarning("Alerts", "No farm selected.")
            return
        with DBHandler() as db:
            results = db.fetch_all(
                """
                SELECT c.date, c.temp_max, m.effective_rainfall
                FROM climate_data c
                LEFT JOIN agri_metrics m ON c.farm_id = m.farm_id AND c.date = m.date
                WHERE c.farm_id=?
                ORDER BY c.date DESC LIMIT 20
                """,
                (self.selected_farm_id,)
            )
        temp_alerts = [f"{date}: {t}°C" for date, t, _ in results if t is not None and t > self.temp_alert_threshold]
        rain_alerts = [f"{date}: {r}mm" for date, _, r in results if r is not None and r < self.rain_alert_threshold]
        msg = ""
        if temp_alerts:
            msg += f"High temperature warning! (>{self.temp_alert_threshold}°C)\n" + "\n".join(temp_alerts) + "\n\n"
        if rain_alerts:
            msg += f"Low effective rainfall warning! (<{self.rain_alert_threshold}mm)\n" + "\n".join(rain_alerts)
        if msg:
            messagebox.showwarning("Alerts", msg)
        else:
            messagebox.showinfo("Alerts", "No alerts. All metrics are normal.")

    # ----- Data Entry/Edit/Delete -----
    def add_entry(self):
        # Add farm or data - choose via dialog
        choice = simpledialog.askstring("Add Entry", "Type 'farm' to add farm, 'data' for climate/agri data:")
        if choice and choice.lower() == "farm":
            name = simpledialog.askstring("Add Farm", "Farm name:")
            loc = simpledialog.askstring("Add Farm", "Location:")
            base = simpledialog.askfloat("Add Farm", "Base temperature (°C):")
            if name and loc and base is not None:
                try:
                    with DBHandler() as db:
                        db.execute_query("INSERT INTO farms (name, location, base_temp) VALUES (?, ?, ?)", (name, loc, base))
                    messagebox.showinfo("Add Farm", f"Farm '{name}' added successfully.")
                except Exception as e:
                    messagebox.showerror("Add Farm Error", f"Failed to add farm: {e}")
                self.load_farms()  # Force refresh farm list
        elif choice and choice.lower() == "data":
            if not self.selected_farm_id:
                messagebox.showwarning("Add Data", "Select a farm first.")
                return
            date = simpledialog.askstring("Add Data", "Date (YYYY-MM-DD):")
            temp_max = simpledialog.askfloat("Add Data", "Max Temp:")
            temp_min = simpledialog.askfloat("Add Data", "Min Temp:")
            rainfall = simpledialog.askfloat("Add Data", "Rainfall (mm):")
            daily_gdd = simpledialog.askfloat("Add Data", "Daily GDD:")
            eff_rain = simpledialog.askfloat("Add Data", "Eff. Rainfall (mm):")
            cum_gdd = simpledialog.askfloat("Add Data", "Cumulative GDD:")
            if date and temp_max is not None and temp_min is not None and rainfall is not None:
                with DBHandler() as db:
                    db.execute_query(
                        "INSERT INTO climate_data (farm_id, date, temp_max, temp_min, rainfall) VALUES (?, ?, ?, ?, ?)",
                        (self.selected_farm_id, date, temp_max, temp_min, rainfall)
                    )
                    db.execute_query(
                        "INSERT INTO agri_metrics (farm_id, date, daily_gdd, effective_rainfall, cumulative_gdd) VALUES (?, ?, ?, ?, ?)",
                        (self.selected_farm_id, date, daily_gdd, eff_rain, cum_gdd)
                    )
                self.refresh_data()

    def edit_entry(self):
        # Edit selected table row (climate data/agri metrics)
        if not hasattr(self, 'table') or self.table is None:
            messagebox.showerror("Edit Error", "Table widget is not initialized. Please refresh or restart the dashboard.")
            return
        sel = self.table.selection()
        if not sel:
            # Try to select the first row automatically
            children = self.table.get_children()
            if children:
                self.table.selection_set(children[0])
                sel = self.table.selection()
            else:
                messagebox.showwarning("Edit", "No rows available to edit.")
                return
        vals = self.table.item(sel[0])["values"]
        if not vals or not self.selected_farm_id:
            messagebox.showerror("Edit Error", "No farm or row selected.")
            return
        date = vals[0]
        temp_max = simpledialog.askfloat("Edit Data", "Max Temp:", initialvalue=float(vals[1]) if vals[1] is not None else None)
        temp_min = simpledialog.askfloat("Edit Data", "Min Temp:", initialvalue=float(vals[2]) if vals[2] is not None else None)
        rainfall = simpledialog.askfloat("Edit Data", "Rainfall:", initialvalue=float(vals[3]) if vals[3] is not None else None)
        daily_gdd = simpledialog.askfloat("Edit Data", "Daily GDD:", initialvalue=float(vals[4]) if vals[4] is not None else None)
        eff_rain = simpledialog.askfloat("Edit Data", "Eff. Rainfall:", initialvalue=float(vals[5]) if vals[5] is not None else None)
        cum_gdd = simpledialog.askfloat("Edit Data", "Cumulative GDD:", initialvalue=float(vals[6]) if vals[6] is not None else None)
        if temp_max is not None and temp_min is not None and rainfall is not None:
            with DBHandler() as db:
                result1 = db.execute_query(
                    "UPDATE climate_data SET temp_max=?, temp_min=?, rainfall=? WHERE farm_id=? AND date=?",
                    (temp_max, temp_min, rainfall, self.selected_farm_id, date)
                )
                result2 = db.execute_query(
                    "UPDATE agri_metrics SET daily_gdd=?, effective_rainfall=?, cumulative_gdd=? WHERE farm_id=? AND date=?",
                    (daily_gdd, eff_rain, cum_gdd, self.selected_farm_id, date)
                )
            if result1 and result2:
                self.refresh_data()
                messagebox.showinfo("Edit", "Entry updated successfully.")
            else:
                messagebox.showerror("Edit Error", "Failed to update entry in database.")

    def delete_entry(self):
        # Delete selected row (climate data/agri metrics)
        if not hasattr(self, 'table') or self.table is None:
            messagebox.showerror("Delete Error", "Table widget is not initialized. Please refresh or restart the dashboard.")
            return
        sel = self.table.selection()
        if not sel:
            # Try to select the first row automatically
            children = self.table.get_children()
            if children:
                self.table.selection_set(children[0])
                sel = self.table.selection()
            else:
                messagebox.showwarning("Delete", "No rows available to delete.")
                return
        vals = self.table.item(sel[0])["values"]
        if not vals or not self.selected_farm_id:
            messagebox.showerror("Delete Error", "No farm or row selected.")
            return
        date = vals[0]
        with DBHandler() as db:
            result1 = db.execute_query(
                "DELETE FROM climate_data WHERE farm_id=? AND date=?",
                (self.selected_farm_id, date)
            )
            result2 = db.execute_query(
                "DELETE FROM agri_metrics WHERE farm_id=? AND date=?",
                (self.selected_farm_id, date)
            )
        if result1 and result2:
            self.refresh_data()
            messagebox.showinfo("Delete", "Entry deleted successfully.")
        else:
            messagebox.showerror("Delete Error", "Failed to delete entry from database.")

    def download_csv_template(self):
        """Download a CSV template for climate data upload."""
        from tkinter import filedialog, messagebox
        template_headers = ["date", "temp_max", "temp_min", "rainfall", "daily_gdd", "eff_rain", "cum_gdd"]
        file_path = filedialog.asksaveasfilename(defaultextension=".csv", filetypes=[("CSV Files", "*.csv")], title="Save CSV Template")
        if not file_path:
            return
        try:
            with open(file_path, "w", newline="") as f:
                writer = csv.writer(f)
                writer.writerow(template_headers)
            messagebox.showinfo("Download Template", f"CSV template saved to {file_path}")
        except Exception as e:
            messagebox.showerror("Download Error", f"Failed to save template: {e}")

    def apply_date_filter(self):
        """Apply date filter to update chart and table based on entered start and end dates."""
        start_date = self.start_date_entry.get().strip()
        end_date = self.end_date_entry.get().strip()
        # If either field is empty, treat as None
        start_date = start_date if start_date else None
        end_date = end_date if end_date else None
        self.update_chart(start_date=start_date, end_date=end_date)

def main():
    root = tb.Window(themename=THEMES[0])
    root.style.theme_use(THEMES[0])
    root.title("Climate & Agri Metrics Dashboard")
    Dashboard(root).pack(fill="both", expand=True)
    root.mainloop()

if __name__ == "__main__":
    main()


