import ttkbootstrap as tb
import tkinter as tk

class HomePage(tb.Frame):
    def __init__(self, parent):
        super().__init__(parent)
        tb.Label(self, text="Welcome to Climate Analysis Dashboard!", font=("Segoe UI", 18, "bold"), padding=20).pack(pady=30)
        tb.Label(self, text="Analyze climate and agricultural metrics with ease.", font=("Segoe UI", 12), padding=10).pack(pady=10)
        tb.Label(
            self,
            text=(
                "This platform helps you manage, visualize, and report farm and climate data.\n"
                "Use the sidebar to navigate between Dashboard, Upload, Visualization, Prediction, and Reports.\n"
                "You can upload your own data, view trends, and generate professional reports.\n"
                "For help or more information, visit the About page."
            ),
            font=("Segoe UI", 11, "italic"),
            padding=10,
            justify="left"
        ).pack(pady=18)

class AboutPage(tb.Frame):
    def __init__(self, parent):
        super().__init__(parent)
        tb.Label(self, text="About", font=("Segoe UI", 18, "bold"), padding=20).pack(pady=(20, 10))
        tb.Label(
            self,
            text=(
                "This tool is designed for visualizing and analyzing climate data. "
                "Users can upload their own datasets and generate custom visualizations to explore trends and patterns in climate variables such as temperature and precipitation."
            ),
            font=("Segoe UI", 12),
            padding=10,
            wraplength=600,
            justify="left"
        ).pack(pady=(0, 18))

        tb.Label(self, text="Features", font=("Segoe UI", 15, "bold"), padding=10).pack(pady=(0, 8))
        features = [
            ("Upload Data", "Add your own datasets for analysis."),
            ("Visualization", "Create charts and graphs of climate data."),
            ("Seasonal Patterns", "Identify seasonal trends in climate variables."),
            ("About", "Learn more about the tool and its capabilities."),
        ]
        for title, desc in features:
            tb.Label(
                self,
                text=f"• \u200b{title}: ",
                font=("Segoe UI", 11, "bold"),
                anchor="w",
                padding=0,
                justify="left"
            ).pack(anchor="w", padx=30)
            tb.Label(
                self,
                text=desc,
                font=("Segoe UI", 11),
                anchor="w",
                padding=0,
                justify="left"
            ).pack(anchor="w", padx=50, pady=(0, 6))
