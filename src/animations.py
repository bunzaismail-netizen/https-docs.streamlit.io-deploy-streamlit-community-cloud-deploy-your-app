# animations.py
"""
Module for handling UI animations and transitions.
Futuristic, 3050-ready effects!
"""

from tkinter import Frame


class Animation:
    """Class for managing simple widget animations."""

    def __init__(self):
        pass

    @staticmethod
    def _interpolate_color(start, end, alpha):
        """Interpolate between two RGB colors. Alpha: 0=start, 1=end."""
        r = int(start[0] * (1 - alpha) + end[0] * alpha)
        g = int(start[1] * (1 - alpha) + end[1] * alpha)
        b = int(start[2] * (1 - alpha) + end[2] * alpha)
        return f"#{r:02x}{g:02x}{b:02x}"

    # -------------------- Fade Animations --------------------
    def fade_in(self, widget, steps=15, delay=18,
                start_color=(34, 34, 59), end_color=(248, 250, 252)):
        """Fade in any widget by changing its background color gradually."""
        widget.lift()
        original_bg = widget.cget("background") if "background" in widget.keys() else None

        def fade(step=0):
            # Check if widget still exists
            try:
                if not getattr(widget, 'winfo_exists', lambda: False)():
                    return
            except Exception:
                return
            alpha = step / steps
            color = self._interpolate_color(start_color, end_color, alpha)
            try:
                widget.configure(bg=color)
            except Exception:
                pass  # ignore if widget has no bg
            if step < steps:
                widget.after(delay, lambda: fade(step + 1))
            else:
                if original_bg:
                    try:
                        widget.configure(bg=original_bg)
                    except Exception:
                        pass

        fade()

    def fade_out(self, widget, steps=15, delay=18,
                 start_color=(248, 250, 252), end_color=(34, 34, 59), callback=None):
        """Fade out any widget by changing its background color gradually."""
        widget.lift()
        original_bg = widget.cget("background") if "background" in widget.keys() else None

        def fade(step=0):
            # Check if widget still exists
            try:
                if not getattr(widget, 'winfo_exists', lambda: False)():
                    return
            except Exception:
                return
            alpha = step / steps
            color = self._interpolate_color(start_color, end_color, alpha)
            try:
                widget.configure(bg=color)
            except Exception:
                pass
            if step < steps:
                widget.after(delay, lambda: fade(step + 1))
            else:
                if callback:
                    callback()
                else:
                    widget.place_forget()
                if original_bg:
                    try:
                        widget.configure(bg=original_bg)
                    except Exception:
                        pass

        fade()

    # -------------------- Slide Animations --------------------
    def slide_in(self, widget, start_x=-800, end_x=0, steps=15, delay=20):
        """Slide a widget from left to right."""
        widget.lift()
        widget.place(x=start_x, y=widget.winfo_y())
        width = end_x - start_x
        step_size = width / steps

        def move(step=0):
            try:
                if not getattr(widget, 'winfo_exists', lambda: False)():
                    return
            except Exception:
                return
            x = start_x + step * step_size
            if (step_size > 0 and x > end_x) or (step_size < 0 and x < end_x):
                x = end_x
            widget.place(x=int(x), y=widget.winfo_y())
            if step < steps and x != end_x:
                widget.after(delay, lambda: move(step + 1))

        move()

    def slide_out(self, widget, end_x=-800, steps=15, delay=20, callback=None):
        """Slide a widget out horizontally."""
        widget.lift()
        start_x = widget.winfo_x()
        width = end_x - start_x
        step_size = width / steps

        def move(step=0):
            x = start_x + step * step_size
            if (step_size > 0 and x > end_x) or (step_size < 0 and x < end_x):
                x = end_x
            widget.place(x=int(x), y=widget.winfo_y())
            if step < steps and x != end_x:
                widget.after(delay, lambda: move(step + 1))
            else:
                if callback:
                    callback()
                else:
                    widget.place_forget()

        move()
