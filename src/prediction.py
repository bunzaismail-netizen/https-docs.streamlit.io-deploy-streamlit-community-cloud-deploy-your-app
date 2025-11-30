import tkinter as tk
import ttkbootstrap as tb
from tkinter import messagebox, filedialog
from db_handler import DBHandler
import joblib
import numpy as np
import os
import csv
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

class PredictionPage(tb.Frame):
    def run_prediction(self):
        if not self.winfo_exists():
            return
        messagebox.showinfo("Predict", "Prediction logic not implemented yet.")
    """
    Page for running climate/agricultural predictions, supporting:
    - Real ML models
    - Batch and per-farm batch predictions
    - Result plots
    - Model info/meta/metrics
    - Cloud API prediction (with API key, error handling)
    - Input validation
    """

    def __init__(self, parent):
        super().__init__(parent, padding=0)
        self.parent = parent

        # Main content area only
        main = tb.Frame(self)
        main.pack(fill="both", expand=True, padx=12, pady=8)

        # Section: Farm selection
        farm_frame = tb.Frame(main)
        farm_frame.pack(anchor="w", pady=(0, 12))
        tb.Label(farm_frame, text="Select Farm:", font=("Segoe UI", 12)).pack(side="left")
        self.farm_combo = tb.Combobox(farm_frame, width=32, state="readonly")
        self.farm_combo.pack(side="left", padx=10)
        self.farm_combo.bind("<<ComboboxSelected>>", self.on_farm_selected)

        # Section: Parameters input (single prediction)
        param_frame = tb.LabelFrame(main, text="Prediction Parameters")
        param_frame.pack(anchor="w", pady=12, fill="x")
        self.temp_var = tk.StringVar()
        self.rain_var = tk.StringVar()
        self.gdd_var = tk.StringVar()
        tb.Label(param_frame, text="Max Temp (°C):").grid(row=0, column=0, sticky="e", padx=5, pady=4)
        tb.Entry(param_frame, textvariable=self.temp_var, width=10).grid(row=0, column=1, padx=5, pady=4)
        tb.Label(param_frame, text="Rainfall (mm):").grid(row=1, column=0, sticky="e", padx=5, pady=4)
        tb.Entry(param_frame, textvariable=self.rain_var, width=10).grid(row=1, column=1, padx=5, pady=4)
        tb.Label(param_frame, text="Cumulative GDD:").grid(row=2, column=0, sticky="e", padx=5, pady=4)
        tb.Entry(param_frame, textvariable=self.gdd_var, width=10).grid(row=2, column=1, padx=5, pady=4)

        # Section: ML Model
        model_frame = tb.LabelFrame(main, text="ML Model")
        model_frame.pack(anchor="w", pady=8, fill="x")
        self.model_path = tk.StringVar(value="No model loaded")
        tb.Label(model_frame, text="ML Model:").pack(side="left")
        self.model_label = tb.Label(model_frame, textvariable=self.model_path, font=("Segoe UI", 9))
        self.model_label.pack(side="left", padx=6)
        tb.Button(model_frame, text="Load Model", style="info.Outline.TButton", command=self.load_model).pack(side="left", padx=5)
        tb.Button(model_frame, text="Model Info", style="secondary.Outline.TButton", command=self.show_model_info).pack(side="left", padx=5)

        # Section: API Key entry for cloud prediction
        api_frame = tb.LabelFrame(main, text="Cloud API")
        api_frame.pack(anchor="w", pady=8, fill="x")
        self.api_key = tk.StringVar()
        tb.Label(api_frame, text="Cloud API Key:", font=("Segoe UI", 10)).pack(side="left")
        tb.Entry(api_frame, textvariable=self.api_key, width=28, show="*").pack(side="left", padx=5)

        # Section: Predict & Export buttons
        btn_frame = tb.Frame(main)
        btn_frame.pack(anchor="w", pady=12)
        tb.Button(btn_frame, text="Predict Yield", style="success.TButton", width=16, command=self.run_prediction).pack(side="left", padx=5)
        tb.Button(btn_frame, text="Export Prediction", style="primary.Outline.TButton", width=18, command=self.export_prediction).pack(side="left", padx=5)
        tb.Button(btn_frame, text="Batch Predict (CSV)", style="info.Outline.TButton", width=20, command=self.batch_predict_csv).pack(side="left", padx=5)
        tb.Button(btn_frame, text="Per-Farm Batch", style="warning.Outline.TButton", width=18, command=self.per_farm_batch).pack(side="left", padx=5)
        tb.Button(btn_frame, text="Cloud API Predict", style="danger.Outline.TButton", width=18, command=self.cloud_api_predict).pack(side="left", padx=5)

        # Section: Prediction result label
        self.result_label = tb.Label(main, text="", font=("Segoe UI", 13, "bold"))
        self.result_label.pack(pady=12)
        # Section: Prediction plot area (defer heavy creation until shown)
        self.fig = None
        self.ax = None
        self.canvas = None
        self._initialized = False
        self._shutdown = False

        # Prediction history
        self.prediction_history = []

        # Load farms
        self.farm_ids = []
        self.load_farms()

        # ML Model placeholder
        self.ml_model = None
        self.model_metrics = None
        self.model_meta = {}

    def load_farms(self):
        """Load farms from the database for selection."""
        with DBHandler() as db:
            farms = db.get_farms()
        if farms:
            self.farm_combo["values"] = [f["name"] for f in farms]
            self.farm_ids = [f["id"] for f in farms]
            self.farm_combo.current(0)
        else:
            self.farm_combo["values"] = []
            self.farm_ids = []
        self.selected_farm_id = self.farm_ids[0] if self.farm_ids else None

    def on_show(self):
        """Lazily create matplotlib figure and canvas when the page becomes visible."""
        if getattr(self, '_initialized', False):
            return
        try:
            self.fig, self.ax = plt.subplots(figsize=(4, 3))
            self.canvas = FigureCanvasTkAgg(self.fig, master=self)
            widget = getattr(self.canvas, 'get_tk_widget', lambda: None)()
            if widget:
                try:
                    widget.pack(pady=10)
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

    def on_farm_selected(self, event=None):
        idx = self.farm_combo.current()
        if 0 <= idx < len(self.farm_ids):
            self.selected_farm_id = self.farm_ids[idx]
        else:
            self.selected_farm_id = None

    def validate_input(self, temp, rain, gdd):
        """Validate input fields for prediction."""
        try:
            temp = float(temp)
            rain = float(rain)
            gdd = float(gdd)
            if not (-50 <= temp <= 60):
                raise ValueError("Temperature out of realistic range.")
            if not (0 <= rain <= 1000):
                raise ValueError("Rainfall out of realistic range.")
            if not (0 <= gdd <= 10000):
                raise ValueError("Cumulative GDD out of realistic range.")
            return temp, rain, gdd
        except Exception as e:
            messagebox.showerror("Input Validation", f"Invalid input: {e}")
            return None

    def load_model(self):
        """Allow user to load a real ML model (scikit-learn joblib format)."""
        model_path = filedialog.askopenfilename(
            title="Select ML Model",
            filetypes=[("Joblib/Pickle Model", "*.joblib *.pkl *.pickle"), ("All Files", "*.*")]
        )
        if model_path and os.path.isfile(model_path):
            try:
                loaded = joblib.load(model_path)
                # If model is a dict (to save meta info, metrics)
                if isinstance(loaded, dict):
                    self.ml_model = loaded.get("model", None)
                    self.model_metrics = loaded.get("metrics", None)
                    self.model_meta = {k: v for k, v in loaded.items() if k not in ("model", "metrics")}
                else:
                    self.ml_model = loaded
                    self.model_metrics = getattr(self.ml_model, "metrics_", None)
                    self.model_meta = {}
                self.model_path.set(os.path.basename(model_path))
                messagebox.showinfo("Model Loaded", f"Loaded model: {os.path.basename(model_path)}")
            except Exception as e:
                self.model_path.set("Load failed")
                self.ml_model = None
                self.model_metrics = None
                self.model_meta = {}
                messagebox.showerror("Error", f"Failed to load model: {e}")

    def show_model_info(self):
        """Display model type, parameters, metrics, and meta info if available."""
        if not self.ml_model:
            messagebox.showwarning("Model Info", "No model loaded.")
            return
        info = f"Model type: {type(self.ml_model).__name__}\n"
        temp, rain, gdd = None, None, None  # Ensure variables are always defined
        if self.ml_model:
            try:
                # Prepare features from current input
                validated = self.validate_input(self.temp_var.get(), self.rain_var.get(), self.gdd_var.get())
                if validated is None:
                    predicted_yield = None
                    result_text = "Invalid input for prediction."
                    style = "danger"
                    temp, rain, gdd = None, None, None
                else:
                    temp, rain, gdd = validated
                    features = np.array([[temp, rain, gdd]])
                    predicted_yield = float(self.ml_model.predict(features)[0])
                    result_text = f"📈 ML Predicted Yield: {predicted_yield:.2f} units"
                    style = "success" if predicted_yield > 0 else "danger"
            except Exception as e:
                predicted_yield = None
                result_text = f"ML Prediction failed: {e}"
                style = "danger"
                temp, rain, gdd = None, None, None
        else:
            validated = self.validate_input(self.temp_var.get(), self.rain_var.get(), self.gdd_var.get())
            if validated is None:
                predicted_yield = None
                result_text = "Invalid input for prediction."
                style = "danger"
                temp, rain, gdd = None, None, None
            else:
                temp, rain, gdd = validated
                k1, k2, k3, base = 0.8, 0.5, 0.03, 10
                predicted_yield = k1 * temp + k2 * rain + k3 * gdd + base
                result_text = f"📈 Predicted Yield: {predicted_yield:.2f} units\n(Load a real model for better accuracy)"
                style = "info"

        self.result_label.config(text=result_text)

        farm_name = self.farm_combo.get() if self.farm_combo.get() else "N/A"
        self.prediction_history.append({
            "farm": farm_name,
            "temperature": temp,
            "rainfall": rain,
            "gdd": gdd,
            "model": self.model_path.get(),
            "predicted_yield": predicted_yield if 'predicted_yield' in locals() else None
        })

        self.plot_predictions()

    def export_prediction(self):
        """Export all predictions made in this session to CSV."""
        if not self.prediction_history:
            messagebox.showwarning("Export", "No predictions to export.")
            return
        file_path = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV Files", "*.csv"), ("All Files", "*.*")]
        )
        if not file_path:
            return
        try:
            with open(file_path, "w", newline="") as f:
                writer = csv.DictWriter(f, fieldnames=["farm", "temperature", "rainfall", "gdd", "model", "predicted_yield"])
                writer.writeheader()
                for entry in self.prediction_history:
                    writer.writerow(entry)
            messagebox.showinfo("Export", f"Predictions exported to:\n{file_path}")
        except Exception as e:
            messagebox.showerror("Export Error", f"Failed to export predictions: {e}")

    def plot_predictions(self):
        """Plot predicted yields from the session."""
        if not getattr(self, '_initialized', False):
            try:
                self.on_show()
            except Exception:
                pass
        if self.ax is None:
            return
        self.ax.clear()
        if self.prediction_history:
            xs = list(range(1, len(self.prediction_history) + 1))
            ys = [entry["predicted_yield"] for entry in self.prediction_history]
            self.ax.plot(xs, ys, marker="o", color="#0d6efd", label="Predicted Yield")
            self.ax.set_title("Predicted Yield History")
            self.ax.set_xlabel("Prediction #")
            self.ax.set_ylabel("Yield")
            self.ax.legend()
        else:
            self.ax.text(0.5, 0.5, "No predictions yet", ha="center", va="center", fontsize=12)
        canvas = getattr(self, 'canvas', None)
        if canvas is not None:
            try:
                canvas.draw()
            except Exception:
                pass

    def batch_predict_csv(self):
        """
        Batch predict yields using a CSV file.
        CSV must have columns: temperature, rainfall, gdd (no header needed).
        """
        file_path = filedialog.askopenfilename(
            title="Select CSV for Batch Prediction",
            filetypes=[("CSV Files", "*.csv"), ("All Files", "*.*")]
        )
        if not file_path or not os.path.isfile(file_path):
            return
        # Read input rows
        rows = []
        try:
            with open(file_path, "r", newline="") as f:
                reader = csv.reader(f)
                for row in reader:
                    if len(row) < 3:
                        continue
                    validated = self.validate_input(row[0], row[1], row[2])
                    if validated:
                        rows.append(validated)
        except Exception as e:
            messagebox.showerror("Read Error", f"Failed to read CSV: {e}")
            return
        if not rows:
            messagebox.showwarning("Batch Predict", "No valid rows found in CSV.")
            return

        features = np.array(rows)
        if self.ml_model:
            try:
                predicts = self.ml_model.predict(features)
            except Exception as e:
                messagebox.showerror("Batch Predict", f"Model prediction error: {e}")
                return
        else:
            k1, k2, k3, base = 0.8, 0.5, 0.03, 10
            predicts = k1 * features[:,0] + k2 * features[:,1] + k3 * features[:,2] + base

        farm_name = self.farm_combo.get() if self.farm_combo.get() else "N/A"
        for i, r in enumerate(rows):
            self.prediction_history.append({
                "farm": farm_name,
                "temperature": r[0],
                "rainfall": r[1],
                "gdd": r[2],
                "model": self.model_path.get(),
                "predicted_yield": float(predicts[i])
            })
        self.plot_predictions()
        messagebox.showinfo("Batch Predict", f"{len(rows)} predictions completed and added to history.")

    def per_farm_batch(self):
        """
        Batch prediction for all available farms, using the same parameters.
        """
        if not self.farm_ids:
            messagebox.showwarning("Batch", "No farms available.")
            return
        validated = self.validate_input(self.temp_var.get(), self.rain_var.get(), self.gdd_var.get())
        if validated is None:
            return
        temp, rain, gdd = validated
        preds = []
        for idx, farm_id in enumerate(self.farm_ids):
            features = np.array([[temp, rain, gdd]])
            if self.ml_model:
                try:
                    predicted_yield = float(self.ml_model.predict(features)[0])
                except Exception as e:
                    predicted_yield = None
            else:
                k1, k2, k3, base = 0.8, 0.5, 0.03, 10
                predicted_yield = k1 * temp + k2 * rain + k3 * gdd + base
            farm_name = self.farm_combo["values"][idx]
            entry = {
                "farm": farm_name,
                "temperature": temp,
                "rainfall": rain,
                "gdd": gdd,
                "model": self.model_path.get(),
                "predicted_yield": predicted_yield
            }
            self.prediction_history.append(entry)
            preds.append(predicted_yield)
        self.plot_predictions()
        messagebox.showinfo("Per-Farm Batch", f"Predicted for all {len(self.farm_ids)} farms.")

    def cloud_api_predict(self):
        """
        Example for cloud API prediction (pseudo code, replace with real API).
        Handles API key and error codes.
        """
        try:
            try:
                import requests
            except ModuleNotFoundError:
                messagebox.showerror("Cloud API", "The 'requests' library is not installed. Please install it using 'pip install requests'.")
                return
        except ImportError:
            messagebox.showerror("Cloud API", "requests library is required.")
            return
        if not self.selected_farm_id:
            messagebox.showwarning("Cloud API", "No farm selected.")
            return
        validated = self.validate_input(self.temp_var.get(), self.rain_var.get(), self.gdd_var.get())
        if validated is None:
            return
        temp, rain, gdd = validated

        api_url = "https://your-api-endpoint/predict"
        payload = {"temperature": temp, "rainfall": rain, "gdd": gdd}
        headers = {}
        if self.api_key.get():
            headers["Authorization"] = f"Bearer {self.api_key.get().strip()}"
        try:
            response = requests.post(api_url, json=payload, headers=headers, timeout=5)
            if response.status_code == 200:
                result = response.json()
                predicted_yield = float(result.get("predicted_yield", 0))
                self.result_label.config(
                    text=f"☁️ Cloud Predicted Yield: {predicted_yield:.2f} units"
                )
                farm_name = self.farm_combo.get() if self.farm_combo.get() else "N/A"
                self.prediction_history.append({
                    "farm": farm_name,
                    "temperature": temp,
                    "rainfall": rain,
                    "gdd": gdd,
                    "model": "Cloud API",
                    "predicted_yield": predicted_yield
                })
                self.plot_predictions()
            elif response.status_code == 401:
                self.result_label.config(
                    text="Cloud API error: Unauthorized (check API key)"
                )
            elif response.status_code == 429:
                self.result_label.config(
                    text="Cloud API error: Rate limit exceeded"
                )
            else:
                self.result_label.config(
                    text=f"Cloud API error: {response.status_code} {response.text}"
                )
        except Exception as e:
            self.result_label.config(
                text=f"Cloud API failed: {e}"
            )

    def get_frame(self):
        return self
    
