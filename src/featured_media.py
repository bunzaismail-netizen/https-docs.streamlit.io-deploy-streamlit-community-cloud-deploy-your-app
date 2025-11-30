from PIL import Image, ImageTk
import ttkbootstrap as tb
import tkinter as tk

class FeaturedMediaFrame(tb.Frame):
    def __init__(self, parent, image_path=None, video_path=None):
        super().__init__(parent)
        if image_path:
            try:
                img = Image.open(image_path)
                img = img.resize((320, 180))
                photo = ImageTk.PhotoImage(img)
                img_label = tb.Label(self, image=photo)
                self._photo = photo  # Keep reference
                img_label.pack(pady=8)
            except Exception as e:
                error_label = tb.Label(self, text=f"Image not found: {image_path}", foreground="red", font=("Segoe UI", 10, "italic"))
                error_label.pack(pady=8)
        # Video support can be added here if needed
