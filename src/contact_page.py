import tkinter as tk

class ContactPage(tk.Frame):
    def __init__(self, parent):
        super().__init__(parent, bg="#f5f5f5")
        tk.Label(self, text="Contact Us", font=("Segoe UI", 20, "bold"), bg="#f5f5f5").pack(pady=24)
        tk.Label(self, text="Email: support@climateapp.com", font=("Segoe UI", 13), bg="#f5f5f5").pack(pady=8)
        tk.Label(self, text="Phone: +1-800-555-CLIM", font=("Segoe UI", 13), bg="#f5f5f5").pack(pady=8)
        tk.Label(self, text="Address: 123 Climate Lane, Green City, Earth", font=("Segoe UI", 12), bg="#f5f5f5").pack(pady=8)
        tk.Label(self, text="We welcome your feedback and inquiries!", font=("Segoe UI", 12), bg="#f5f5f5").pack(pady=16)

    def get_frame(self):
        return self
