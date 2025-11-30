import tkinter as tk
import ttkbootstrap as tb
from tkinter import messagebox, simpledialog
import threading
import time
import sys, traceback

# Module-level diagnostic hooks: log Tk callback exceptions and thread exceptions early
def _tk_report_callback_exception(exc, val, tb):
    try:
        # If the application has been destroyed, Tk may raise a TclError
        msg = ''
        try:
            msg = str(val)
        except Exception:
            msg = ''
        if 'application has been destroyed' in msg or "can't invoke \"tk\" command" in msg:
            print('[DIAG] Tk callback attempted after application destroy; suppressed.')
            return
    except Exception:
        pass
    print("[DIAG] Tk callback exception:")
    traceback.print_exception(exc, val, tb)

try:
    # assign to Tk class so it's active for all instances
    tk.Tk.report_callback_exception = _tk_report_callback_exception
except Exception:
    pass

def _thread_excepthook(args):
    print("[DIAG] Uncaught thread exception:")
    try:
        traceback.print_exception(args.exc_type, args.exc_value, args.exc_traceback)
    except Exception:
        print(args)

try:
    if hasattr(threading, 'excepthook'):
        threading.excepthook = _thread_excepthook
except Exception:
    pass

# Instrument threading.Thread.run to log exceptions from any thread (diagnostic)
try:
    _orig_thread_run = threading.Thread.run
    def _thread_run_with_logging(self, *args, **kwargs):
        try:
            return _orig_thread_run(self, *args, **kwargs)
        except Exception:
            import traceback
            print("[DIAG] Exception in thread (from patched run):")
            traceback.print_exc()
            raise
    threading.Thread.run = _thread_run_with_logging
except Exception:
    pass

# Page modules are imported lazily in factories to speed up startup

# --- Splash Screen ---
class SplashScreen(tk.Toplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.geometry("400x250+500+250")
        self.overrideredirect(True)
        self.configure(bg="#384e77")
        label = tk.Label(self, text="🌦️ Climate Analysis Dashboard", font=("Segoe UI", 22, "bold"), fg="white", bg="#384e77")
        label.pack(pady=50)
        sub = tk.Label(self, text="Loading...", font=("Segoe UI", 12), fg="white", bg="#384e77")
        sub.pack()
        self.update()

# --- Login Dialog ---
class LoginDialog(simpledialog.Dialog):
    def body(self, master):
        tk.Label(master, text="Username:").grid(row=0)
        tk.Label(master, text="Password:").grid(row=1)
        self.username = tk.Entry(master)
        self.password = tk.Entry(master, show="*")
        self.username.grid(row=0, column=1)
        self.password.grid(row=1, column=1)
        return self.username

    def apply(self):
        self.result = (self.username.get(), self.password.get())

# --- Advanced Sidebar ---
class Sidebar(tb.Frame):
    def __init__(self, parent, show_page, user, logout_callback, *args, **kwargs):
        super().__init__(parent, height=60, *args, **kwargs)
        self.show_page = show_page
        self.logout_callback = logout_callback
        self.user = user
        # Add subtle shadow/border below topbar using a separator
        sep = tb.Separator(self, orient="horizontal")
        sep.pack(side="top", fill="x")

        # Topbar header
        header = tb.Label(self, text="Climate Dashboard", font=("Segoe UI", 15, "bold"), background="#0d6efd", foreground="white", padding=12)
        header.pack(side="left", padx=(10, 20))

        # Notification bell icon (with badge)
        notif_frame = tb.Frame(self, style="primary.TFrame")
        notif_frame.pack(side="left", padx=(0, 8))
        self.notif_count = tk.IntVar(value=3)
        notif_btn = tb.Button(notif_frame, text="🔔", style="secondary.TButton", width=3)
        notif_btn.pack(side="left")
        notif_badge = tk.Label(notif_frame, textvariable=self.notif_count, font=("Segoe UI", 8, "bold"), bg="#dc3545", fg="white", width=2)
        notif_badge.place(x=28, y=0)

        # Settings button
        settings_btn = tb.Button(self, text="⚙️", style="secondary.TButton", width=3)
        settings_btn.pack(side="left", padx=(0, 8))

        # Navigation bar (vertical)
        nav_frame = tb.Frame(self, style="primary.TFrame")
        nav_frame.pack(side="top", fill="y", padx=10)
        self.btns = {}
        nav_sections = [
            ("Main", [
                ("Home", "home", "🏡"),
                ("Dashboard", "dashboard", "🏠"),
                ("Upload Data", "upload", "⬆️"),
            ]),
            ("Analysis", [
                ("Visualization", "visualization", "📊"),
                ("Prediction", "prediction", "🔮"),
                ("Reports", "report", "📑"),
            ]),
            ("Info", [
                ("About", "about", "ℹ️"),
            ]),
        ]
        for sec_idx, (section, items) in enumerate(nav_sections):
            sec_frame = tb.LabelFrame(nav_frame, text=section, style="primary.TLabelframe")
            sec_frame.pack(side="top", fill="x", padx=2, pady=2)
            for idx, (name, key, emoji) in enumerate(items):
                btn = tb.Button(
                    sec_frame, text=f"{emoji} {name}", style="secondary.TButton", width=15,
                    command=lambda k=key:self._on_nav_click(k)
                )
                btn.pack(side="top", fill="x", padx=4, pady=2)
                btn.bind("<Enter>", lambda e, b=btn: b.configure(style="info.TButton"))
                btn.bind("<Leave>", lambda e, b=btn: b.configure(style="secondary.TButton"))
                btn.bind("<FocusIn>", lambda e, b=btn: b.configure(style="success.TButton"))
                btn.bind("<FocusOut>", lambda e, b=btn: b.configure(style="secondary.TButton"))
                self.btns[key] = btn
                # Tooltip for each button
                btn.bind("<Enter>", lambda e, b=btn, t=name: self._show_tooltip(b, t))
                btn.bind("<Leave>", lambda e: self._hide_tooltip())
                # Keyboard shortcut: Alt+1, Alt+2, ...
                self.bind_all(f"<Alt-Key-{sec_idx*3+idx+1}>", lambda e, k=key: self._on_nav_click(k))
        self.active_key = None
        self._tooltip = None
        nav_sections = [
            ("Main", [
                ("Home", "home", "🏡"),
                ("Dashboard", "dashboard", "🏠"),
                ("Upload Data", "upload", "⬆️"),
            ]),
            ("Analysis", [
                ("Visualization", "visualization", "📊"),
                ("Prediction", "prediction", "🔮"),
                ("Reports", "report", "📑"),
            ]),
            ("Info", [
                ("About", "about", "ℹ️"),
            ]),
        ]
        self.btns = {}
        for sec_idx, (section, items) in enumerate(nav_sections):
            sec_frame = tb.LabelFrame(nav_frame, text=section, style="primary.TLabelframe")
            sec_frame.pack(side="top", fill="x", padx=2, pady=2)
            for idx, (name, key, emoji) in enumerate(items):
                btn = tb.Button(
                    sec_frame, text=f"{emoji} {name}", style="secondary.TButton", width=15,
                    command=lambda k=key:self._on_nav_click(k)
                )
                btn.pack(side="top", fill="x", padx=4, pady=2)
                btn.bind("<Enter>", lambda e, b=btn: b.configure(style="info.TButton"))
                btn.bind("<Leave>", lambda e, b=btn: b.configure(style="secondary.TButton"))
                btn.bind("<FocusIn>", lambda e, b=btn: b.configure(style="success.TButton"))
                btn.bind("<FocusOut>", lambda e, b=btn: b.configure(style="secondary.TButton"))
                self.btns[key] = btn
                # Tooltip for each button
                btn.bind("<Enter>", lambda e, b=btn, t=name: self._show_tooltip(b, t))
                btn.bind("<Leave>", lambda e: self._hide_tooltip())
                # Keyboard shortcut: Alt+1, Alt+2, ...
                self.bind_all(f"<Alt-Key-{sec_idx*3+idx+1}>", lambda e, k=key: self._on_nav_click(k))

        self.active_key = None
        self._tooltip = None

    def _show_tooltip(self, widget, text):
        if self._tooltip:
            self._hide_tooltip()
        x = widget.winfo_rootx() + 60
        y = widget.winfo_rooty() + 10
        self._tooltip = tk.Toplevel(widget)
        self._tooltip.wm_overrideredirect(True)
        self._tooltip.wm_geometry(f"+{x}+{y}")
        label = tk.Label(self._tooltip, text=text, background="#ffffe0", relief="solid", borderwidth=1, font=("Segoe UI", 9))
        label.pack(ipadx=4, ipady=2)

    def _hide_tooltip(self):
        if self._tooltip:
            self._tooltip.destroy()
            self._tooltip = None

        self.active_key = None

    def _on_nav_click(self, key):
        # Highlight active button
        for k, btn in self.btns.items():
            if k == key:
                            btn.configure(style="success.TButton")
            else:
                            btn.configure(style="secondary.TButton")
        self.active_key = key
        self.show_page(key)

        # Spacer
        tb.Label(self, text="", width=2, background="#0d6efd").pack(side="left")

        # User info with avatar/initials
        user_frame = tb.Frame(self, style="primary.TFrame")
        user_frame.pack(side="left", padx=(0, 10))
        username = self.user.get("username", "User")
        initials = ''.join([x[0] for x in username.split()]).upper()[:2]
        avatar = tk.Label(user_frame, text=initials if initials else "👤", font=("Segoe UI", 13, "bold"), bg="#0d6efd", fg="white", width=3, relief="groove")
        avatar.pack(side="left", padx=(0,4))
        user_info = tk.Label(user_frame, text=username, font=("Segoe UI", 11, "bold"), bg="#0d6efd", fg="white")
        user_info.pack(side="left")

        # Date/time display
        self.datetime_var = tk.StringVar()
        dt_label = tk.Label(self, textvariable=self.datetime_var, font=("Segoe UI", 10), bg="#0d6efd", fg="#d7d7d7")
        dt_label.pack(side="right", padx=(0, 12))
        self._update_datetime()

        # Logout button
        tb.Button(self, text="Logout", style="danger.Outline.TButton", command=self.logout_callback, width=10).pack(side="right", padx=12, pady=8)

        # Theme switcher
        theme_frame = tb.Frame(self, style="primary.TFrame")
        theme_frame.pack(side="right", padx=8)
        tk.Label(theme_frame, text="Theme:", font=("Segoe UI", 9), bg="#0d6efd", fg="#d7d7d7").pack(side="left")
        self.theme_var = tk.StringVar(value="flatly")
        themes = ["flatly", "superhero", "darkly", "cosmo", "journal", "litera", "sandstone", "yeti"]
        theme_combo = tb.Combobox(theme_frame, values=themes, textvariable=self.theme_var, state="readonly", width=11)
        theme_combo.pack(side="left", padx=5)
        self.theme_switch_callback = None
        theme_combo.bind("<<ComboboxSelected>>", self._switch_theme)

    def _update_datetime(self):
        import datetime
        if not hasattr(self, 'datetime_var') or not self.winfo_exists():
            return
        now = datetime.datetime.now().strftime('%a %d %b %Y, %H:%M')
        self.datetime_var.set(now)
        if self.winfo_exists():
            self._after_id = self.after(60000, self._update_datetime)  # update every minute

    def destroy(self):
        # Cancel scheduled after callback to prevent background errors
        if hasattr(self, '_after_id'):
            try:
                self.after_cancel(self._after_id)
            except Exception:
                pass
        super().destroy()

    def set_theme_callback(self, func):
        self.theme_switch_callback = func

    def _switch_theme(self, event=None):
        if self.theme_switch_callback:
            self.theme_switch_callback(self.theme_var.get())

class ClimateApp(tk.Tk):
    """
    Main application window for the Climate Analysis Dashboard.
    Supports authentication, splash screen, advanced sidebar, and dynamic theme switching.
    """
    def __init__(self, tk_root=None):
        super().__init__()

        # Header frame with app logo, avatar, notification badge, theme switcher
        self.header = tk.Frame(self, bg="#0d6efd", height=56)
        self.header.pack(side="top", fill="x")
        logo = tk.Label(self.header, text="🌦️", font=("Segoe UI", 22, "bold"), bg="#0d6efd", fg="white")
        logo.pack(side="left", padx=(12, 8))
        app_title = tk.Label(self.header, text="Climate Analysis Dashboard", font=("Segoe UI", 16, "bold"), bg="#0d6efd", fg="white")
        app_title.pack(side="left", padx=(0, 18))
        # Notification badge
        notif_frame = tk.Frame(self.header, bg="#0d6efd")
        notif_frame.pack(side="right", padx=(0, 12))
        notif_icon = tk.Label(notif_frame, text="🔔", font=("Segoe UI", 16), bg="#0d6efd", fg="white")
        notif_icon.pack(side="left")
        notif_badge = tk.Label(notif_frame, text="3", font=("Segoe UI", 9, "bold"), bg="#dc3545", fg="white", width=2)
        notif_badge.place(x=28, y=0)
        # User avatar
        avatar_frame = tk.Frame(self.header, bg="#0d6efd")
        avatar_frame.pack(side="right", padx=(0, 8))
        username = getattr(self, 'logged_in_user', {"username": "User"}).get("username", "User")
        initials = ''.join([x[0] for x in username.split()]).upper()[:2]
        avatar = tk.Label(avatar_frame, text=initials if initials else "👤", font=("Segoe UI", 13, "bold"), bg="#0d6efd", fg="white", width=3, relief="groove")
        avatar.pack(side="left", padx=(0,4))
        # Theme switcher
        theme_var = tk.StringVar(value="flatly")
        theme_combo = tb.Combobox(self.header, values=["flatly", "superhero", "darkly", "cosmo", "journal", "litera", "sandstone", "yeti"], textvariable=theme_var, state="readonly", width=11)
        theme_combo.pack(side="right", padx=8)
        theme_combo.bind("<<ComboboxSelected>>", lambda e: self.switch_theme(theme_var.get()))

    # Sidebar will be created after login
    # Ensure sidebar is packed to the left side for vertical navigation

        # Install diagnostic hooks to capture background exceptions and Tk callback errors.
        try:
            import sys, traceback
            # Tkinter exception handler for callback errors
            def tk_report_callback_exception(self, exc, val, tb):
                print("Tk background error captured:")
                traceback.print_exception(exc, val, tb)
            try:
                # bind to this Tk instance's callback exception hook
                setattr(self, 'report_callback_exception', tk_report_callback_exception.__get__(self, tk.Tk))
            except Exception:
                pass

            # Threading excepthook to log exceptions from threads
            def thread_excepthook(args):
                print("Thread exception in thread:\n", args)
                try:
                    traceback.print_exception(args.exc_type, args.exc_value, args.exc_traceback)
                except Exception:
                    pass
            try:
                import threading as _th
                if hasattr(_th, 'excepthook'):
                    _th.excepthook = thread_excepthook
            except Exception:
                pass
        except Exception:
            pass

        # Install one-shot Tk callback diagnostic to capture any remaining bgerror in a log file
        try:
            from tk_diagnostics import install_reporter
            try:
                setattr(self, 'report_callback_exception', install_reporter(self))
            except Exception:
                pass
        except Exception:
            pass

        # Window setup
        self.title("Climate Analysis Dashboard")
        self.geometry("1200x700")
        self.configure(bg="#f5f5f5")

        # Theme management
        self.theme_name = tk.StringVar(value="flatly")
        # Initialize ttkbootstrap.Style in a safe, deferred manner so theme setup
        # doesn't try to touch widgets that may be in the process of being
        # created/destroyed (this avoids Tcl errors in test/headless flows).
        self.app_style = None
        def _init_style():
            try:
                self.app_style = tb.Style(self.theme_name.get())
            except Exception:
                try:
                    # Fallback to default Style if the requested theme fails
                    self.app_style = tb.Style()
                except Exception:
                    self.app_style = None
        try:
            # Use after to defer style initialization until the Tk loop is ready.
            self.after(0, _init_style)
        except Exception:
            # If after isn't available for some reason, try immediate init.
            _init_style()

        # Start with login page
        self.logged_in_user = None
        self.sidebar = None
        self.pages = {}
        self.current_page = None

        # Lazy import LoginPage to avoid heavy imports at startup
        from login_page import LoginPage as _LoginPage
        self.login_page = _LoginPage(self, self.on_login)
        self.login_page.pack(fill="both", expand=True)
        print("[DIAG] Login page packed.")

        # Force sidebar and home page for debugging
        import os
        if os.environ.get("CLIMATE_DEBUG_UI", "1") == "1":
            self.logged_in_user = {"username": "User", "role": "user"}
            print("[DIAG] Forcing sidebar and home page display.")
            self.sidebar = Sidebar(self, self.show_page, self.logged_in_user, self.logout)
            self.sidebar.pack(side="left", fill="y")
            self.sidebar.set_theme_callback(self.switch_theme)
            self.setup_pages()
            self.show_page("home")

    def on_login(self, username):
        print(f"[DIAG] on_login called with username: {username}")
        # Fetch user role from DB
        import sqlite3
        from db_handler import DBHandler
        with DBHandler() as db:
            user_row = db.fetch_one("SELECT role FROM users WHERE username=?", (username,))
            role = user_row[0] if user_row else "user"
        self.logged_in_user = {"username": username, "role": role}
        self.login_page.pack_forget()
        # Show sidebar and main pages
        self.sidebar = Sidebar(self, self.show_page, self.logged_in_user, self.logout)
        self.sidebar.pack(side="left", fill="y")
        self.sidebar.set_theme_callback(self.switch_theme)
        self.setup_pages()
        self.show_page("home")

    def setup_pages(self):
        # Only set up page factories, do not create a new header
        def home_factory():
            try:
                from home_about import HomePage
                return HomePage(self)
            except ImportError:
                frame = tk.Frame(self, bg="#cce5ff")
                tk.Label(frame, text="Home", font=("Segoe UI", 18, "bold"), bg="#cce5ff").pack(pady=24)
                return frame

        def about_factory():
            from home_about import AboutPage
            return AboutPage(self)

        def contact_factory():
            try:
                from contact_page import ContactPage
                return ContactPage(self)
            except ImportError:
                frame = tk.Frame(self, bg="#f5f5f5")
                tk.Label(frame, text="Contact Us", font=("Segoe UI", 18, "bold"), bg="#f5f5f5").pack(pady=24)
                tk.Label(frame, text="Email: support@climateapp.com\nPhone: +1-800-555-CLIM", font=("Segoe UI", 12), bg="#f5f5f5").pack(pady=8)
                return frame

        def dashboard_factory():
            from dashboard import Dashboard
            return Dashboard(self)

        def upload_factory():
            from upload_page import UploadPage
            return UploadPage(self)

        def visualization_factory():
            from visualization import VisualizationPage
            return VisualizationPage(self, user=self.logged_in_user)

        # NOTE: Swap factories so the Report navigation shows Prediction content
        # and the Prediction navigation shows Report content as requested.
        def prediction_factory():
            # Intentionally return the Report page when user clicks Prediction
            from report_page import ReportPage
            return ReportPage(self)

        def report_factory():
            # Intentionally return the Prediction page when user clicks Reports
            from prediction import PredictionPage
            return PredictionPage(self)

        def user_management_factory():
            try:
                from user_management import UserManagementPage
                return UserManagementPage(self, user=self.logged_in_user)
            except ImportError:
                return None

        self.page_factories = {
            "home": home_factory,
            "about": about_factory,
            "contact": contact_factory,
            "dashboard": dashboard_factory,
            "upload": upload_factory,
            "visualization": visualization_factory,
            "prediction": prediction_factory,
            "report": report_factory,
            "user_management": user_management_factory if self.logged_in_user and self.logged_in_user["role"] == "admin" else None,
        }
        self.pages = {}

    def switch_theme(self, theme):
        """Instant theme preview and accessibility high-contrast support."""
        try:
            if self.app_style:
                self.app_style.theme_use(theme)
            # Accessibility: high-contrast mode for dark themes
            if theme in ["darkly", "superhero"]:
                self.configure(bg="#222")
                if hasattr(self, 'sidebar') and self.sidebar:
                    try:
                        self.sidebar['style'] = "dark.TFrame"
                    except Exception:
                        pass
                if hasattr(self, 'header') and self.header:
                    try:
                        self.header['bg'] = "#222"
                    except Exception:
                        pass
            else:
                self.configure(bg="#f5f5f5")
                if hasattr(self, 'sidebar') and self.sidebar:
                    try:
                        self.sidebar['style'] = "primary.TFrame"
                    except Exception:
                        pass
                if hasattr(self, 'header') and self.header:
                    try:
                        self.header['bg'] = "#0d6efd"
                    except Exception:
                        pass
        except Exception:
            pass

    def show_page(self, page_name):
        print(f"[DIAG] show_page called for: {page_name}")
        """Switch between pages with fade transition and accessibility focus."""
        # Hide current page (if any) with fade out
        if self.current_page:
            try:
                cur = self.current_page.get_frame() if hasattr(self.current_page, 'get_frame') else self.current_page
                pf = getattr(cur, 'pack_forget', None)
                if callable(pf):
                    # Fade out effect (Windows only supports alpha on toplevel)
                    win = None
                    try:
                        win = cur.winfo_toplevel()
                        for alpha in range(100, 0, -20):
                            win.attributes('-alpha', alpha/100)
                            win.update_idletasks()
                            self.update()
                    except Exception:
                        pass
                    pf()
                    try:
                        if win is not None:
                            win.attributes('-alpha', 1.0)
                    except Exception:
                        pass
            except Exception:
                pass

        # If page already instantiated, use it. Otherwise, instantiate from factory.
        page = self.pages.get(page_name)
        if page is None:
            factory = getattr(self, 'page_factories', {}).get(page_name)
            if not factory:
                messagebox.showinfo("Access Denied", "You do not have access to this feature.")
                return
            try:
                page = factory()
                self.pages[page_name] = page
            except Exception as e:
                messagebox.showerror("Page Error", f"Failed to open page {page_name}: {e}")
                return

        frame = page.get_frame() if hasattr(page, "get_frame") else page
        if frame is None:
            messagebox.showerror("Page Error", f"Failed to open page {page_name}.")
            return
        try:
            # Always pack main page frame to right of sidebar
            frame.pack(side="right", fill="both", expand=True)
            try:
                win = frame.winfo_toplevel()
                for alpha in range(0, 101, 20):
                    win.attributes('-alpha', alpha/100)
                    win.update_idletasks()
                    self.update()
                win.attributes('-alpha', 1.0)
            except Exception:
                pass
        except Exception:
            try:
                pack_fn = getattr(frame, 'pack', None)
                if callable(pack_fn):
                    pack_fn(side="right", fill="both", expand=True)
            except Exception:
                pass

        # Accessibility: set focus to first widget in the page
        try:
            first_widget = frame.winfo_children()[0] if frame.winfo_children() else frame
            first_widget.focus_set()
        except Exception:
            pass

        # Remember the current page object for future hide/destroy operations
        try:
            self.current_page = page
        except Exception:
            self.current_page = None

        # Allow pages to lazily initialize heavy widgets when they become visible
        try:
            if hasattr(page, 'on_show'):
                page.on_show()
        except Exception:
            pass

    def logout(self):
        if messagebox.askokcancel("Logout", "Are you sure you want to logout?"):
            # Attempt graceful shutdown: notify pages to stop background work and destroy resources
            try:
                for name, page in list(getattr(self, 'pages', {}).items()):
                    try:
                        if page is None:
                            continue
                        # If page object exposes _shutdown flag, set it so background workers stop
                        try:
                            if hasattr(page, '_shutdown'):
                                setattr(page, '_shutdown', True)
                        except Exception:
                            pass
                        # Call common stop methods if available
                        for stop_name in ('stop_schedule', 'stop', 'stop_socket', 'stop_listener', 'close', 'shutdown'):
                            fn = getattr(page, stop_name, None)
                            if callable(fn):
                                try:
                                    fn()
                                except Exception:
                                    pass
                        # Try to destroy page/frame resources
                        try:
                            d = getattr(page, 'destroy', None)
                            if callable(d):
                                d()
                        except Exception:
                            pass
                    except Exception:
                        pass
            except Exception:
                pass
            # Also ensure sidebar is stopped/destroyed (it has its own after callbacks)
            try:
                if hasattr(self, 'sidebar') and self.sidebar:
                    try:
                        setattr(self.sidebar, '_shutdown', True)
                    except Exception:
                        pass
                    try:
                        # cancel sidebar scheduled update if present
                        aid = getattr(self.sidebar, '_after_id', None)
                        if aid is not None:
                            try:
                                self.sidebar.after_cancel(aid)
                            except Exception:
                                pass
                    except Exception:
                        pass
                    try:
                        self.sidebar.destroy()
                    except Exception:
                        pass
            except Exception:
                pass
            # Cancel any top-level scheduled callbacks on the app
            try:
                aid = getattr(self, '_after_id', None)
                if aid is not None:
                    try:
                        self.after_cancel(aid)
                    except Exception:
                        pass
            except Exception:
                pass
            # Now safely destroy application
            self.destroy()
            # Optionally restart the app for new login
            import sys, subprocess
            subprocess.Popen([sys.executable] + sys.argv)
            exit(0)
    def refresh_dashboard(self):
        # Remove current dashboard frame
        if "dashboard" in self.pages:
            try:
                existing = self.pages["dashboard"]
                # If it wraps a frame, get that; else assume it's a frame
                frame = existing.get_frame() if hasattr(existing, 'get_frame') else existing
                pf = getattr(frame, 'pack_forget', None)
                if callable(pf):
                    pf()
                # Prefer calling destroy on the object that owns resources
                d = getattr(existing, 'destroy', None) or getattr(frame, 'destroy', None)
                if callable(d):
                    d()
            except Exception:
                pass
        # Recreate dashboard frame using factory if available
        factory = getattr(self, 'page_factories', {}).get('dashboard')
        if factory:
            try:
                self.pages["dashboard"] = factory()
            except Exception:
                self.pages["dashboard"] = None
        else:
            self.pages["dashboard"] = None
        if self.current_page == self.pages["dashboard"]:
            self.current_page = self.pages["dashboard"]
            try:
                pack_fn = getattr(self.current_page, 'pack', None)
                if callable(pack_fn):
                    pack_fn(fill="both", expand=True)
            except Exception:
                pass

if __name__ == "__main__":
    app = ClimateApp()
    app.mainloop()