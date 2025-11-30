import tkinter as tk
import ttkbootstrap as tb
from tkinter import messagebox, simpledialog
import threading
from notifications import register as register_notif, unregister as unregister_notif
try:
    import socketio  # Requires `pip install python-socketio`
    _HAS_SOCKETIO = True
except Exception:
    socketio = None
    _HAS_SOCKETIO = False

class Sidebar(tb.Frame):
    """
    Fully-featured sidebar with:
      - Navigation, user info, theme switching, notifications (live via sockets)
      - User settings, API quota, session stats, admin tools, and extensible widgets
    """
    def __init__(self, parent, show_page, user, logout_callback, *args, **kwargs):
        super().__init__(parent, style="dark.TFrame", width=230, *args, **kwargs)
        self.show_page = show_page
        self.logout_callback = logout_callback
        self.user = user or {"username": "Guest", "role": "user", "email": ""}
        self.configure(borderwidth=0)
        self.notifications = []
        self.theme_switch_callback = None
        self.session_actions = 0
        self.api_quota = 100  # Example quota
        self.backend_url = "http://localhost:8080"  # Update with your backend
        self.socketio_client = None
        self.socket_thread = None
        self.socket_connected = False
        # Register with global notifications center so backend events show in the sidebar
        try:
            register_notif(self)
        except Exception:
            pass

    def stop_socket(self):
        try:
            setattr(self, '_shutdown', True)
        except Exception:
            pass
        try:
            if not _HAS_SOCKETIO:
                return
            sio = getattr(self, 'socketio_client', None)
            if sio is not None:
                try:
                    # some static checkers may think socketio_client could be None
                    sio.disconnect()
                except Exception:
                    pass
        except Exception:
            pass
        try:
            unregister_notif(self)
        except Exception:
            pass

        # User section
        user_frame = tb.Frame(self, style="dark.TFrame")
        user_frame.pack(fill="x", padx=10, pady=(10,3))
        icon = tk.Label(user_frame, text="👤", font=("Segoe UI", 16), bg="#212529", fg="white")
        icon.pack(side="left", padx=(0,8))
        user_info = tk.Label(
            user_frame,
            text=f"{self.user.get('username', 'User')} ({self.user.get('role', 'user')})",
            font=("Segoe UI", 12, "bold"),
            bg="#212529", fg="white"
        )
        user_info.pack(side="left")


        # Notification icon/button
        notif_frame = tb.Frame(self, style="dark.TFrame")
        notif_frame.pack(fill="x", padx=10, pady=(0,3))
        self.notif_btn = tb.Button(
            notif_frame, text="🔔 Notifications", style="secondary-outline.TButton", command=self.show_notifications
        )
        self.notif_btn.pack(side="left", fill="x", expand=True)
        self.notif_count_label = tk.Label(
            notif_frame, text="", font=("Segoe UI", 10, "bold"), bg="#212529", fg="yellow"
        )
        self.notif_count_label.pack(side="left", padx=(6,0))
        self.update_notif_badge()

        # User settings widget
        settings_frame = tb.Frame(self, style="dark.TFrame")
        settings_frame.pack(fill="x", padx=10, pady=(0,3))
        tb.Button(settings_frame, text="⚙️ Settings", style="secondary-outline.TButton", command=self.show_user_settings).pack(side="left", fill="x", expand=True)

        # Quick stats widgets: session actions, API quota, and more ideas below
        stats_frame = tb.Frame(self, style="dark.TFrame")
        stats_frame.pack(fill="x", padx=10, pady=(0,2))
        self.stats_label = tk.Label(stats_frame, text="Session: 0 actions", font=("Segoe UI", 9), bg="#212529", fg="#7dcfff")
        self.stats_label.pack(side="left", anchor="w")
        self.api_quota_label = tk.Label(stats_frame, text=f"API Quota: {self.api_quota}", font=("Segoe UI", 9), bg="#212529", fg="#ffcc99")
        self.api_quota_label.pack(side="left", padx=(8,0))
        # --- More widget ideas: ---
        self.sync_label = tk.Label(stats_frame, text="⏳ Not synced", font=("Segoe UI", 9), bg="#212529", fg="#ff99cc")
        self.sync_label.pack(side="left", padx=(8,0))
        # Could also add: Last login time, unread messages, online users, workflow status, etc.

        # Shortcut: Refresh Data
        tb.Button(self, text="🔄 Refresh Data", style="secondary-outline.TButton", command=self.refresh_data).pack(pady=(4,2), padx=10, fill="x")

        # Logout button
        tb.Button(self, text="Logout", style="danger-outline.TButton",command=self.logout_callback).pack(pady=(0,20), padx=10, fill="x")

        # Navigation
        self.btns = {}
        nav_items = [
            ("Dashboard", "dashboard", "🏠"),
            ("Visualization", "visualization", "📊"),
            ("Prediction", "prediction", "🔮"),
            ("Reports", "report", "📑"),
        ]
        # Only show Upload Data for admin
        if self.user.get("role", "user") == "admin":
            nav_items.insert(1, ("Upload Data", "upload", "⬆️"))
            nav_items.append(("User Management", "user_management", "👥"))
        for name, key, emoji in nav_items:
            self.btns[key] = tb.Button(
                self, text=f"{emoji} {name}", style="secondary.TButton", width=21,
                command=lambda k=key:self._navigate(k)
            )
            self.btns[key].pack(pady=4, padx=8, fill="x")

        # Admin section
        if self.user.get("role", "user") == "admin":
            admin_label = tk.Label(self, text="Admin Tools", bg="#212529", fg="#ffcc00", font=("Segoe UI", 10, "bold"))
            admin_label.pack(pady=(20,0), padx=10, anchor="w")
            tb.Button(self, text="Global Analytics", style="dark-outline.TButton", width=21, command=lambda: self.show_page("report")).pack(pady=4, padx=8, fill="x")
            tb.Button(self, text="User Management", style="secondary-outline.TButton", width=21, command=lambda: self.show_page("user_management")).pack(pady=2, padx=8, fill="x")
            tb.Button(self, text="Send System Alert", style="warning-outline.TButton", width=21, command=self.send_system_alert).pack(pady=2, padx=8, fill="x")

        # Theme switcher
        theme_frame = tb.Frame(self, style="dark.TFrame")
        theme_frame.pack(side="bottom", pady=16, padx=8, fill="x")
        tk.Label(theme_frame, text="Theme:", font=("Segoe UI", 9), bg="#212529", fg="#d7d7d7").pack(side="left")
        self.theme_var = tk.StringVar(value="flatly")
        themes = ["flatly", "superhero", "darkly", "cosmo", "journal", "litera", "sandstone", "yeti"]
        theme_combo = tb.Combobox(theme_frame, values=themes, textvariable=self.theme_var, state="readonly", width=11)
        theme_combo.pack(side="left", padx=5)
        theme_combo.bind("<<ComboboxSelected>>", self._switch_theme)

        # Start socket.io listener for live backend events
        self.start_socket_listener()

    def _navigate(self, key):
        self.session_actions += 1
        self.stats_label.config(text=f"Session: {self.session_actions} actions")
        self.show_page(key)

    def set_theme_callback(self, func):
        self.theme_switch_callback = func

    def _switch_theme(self, event=None):
        if self.theme_switch_callback:
            self.theme_switch_callback(self.theme_var.get())

    # --- Notifications ---
    def show_notifications(self):
        if not self.notifications:
            messagebox.showinfo("Notifications", "No notifications.")
            return
        top = tk.Toplevel(self)
        top.title("Notifications")
        text = tk.Text(top, width=60, height=16, font=("Segoe UI", 10))
        text.pack(fill="both", expand=True)
        for i, notif in enumerate(self.notifications, 1):
            text.insert(tk.END, f"{i}. {notif}\n")
        text.config(state="disabled")
        tb.Button(top, text="Clear All", style="danger.TButton", command=lambda: self.clear_notifications(top)).pack(pady=8)

    def update_notif_badge(self):
        # Always update the badge on the main thread
        def _upd():
            try:
                count = len(self.notifications)
                self.notif_count_label.config(text=f"{count}" if count else "")
            except Exception:
                pass
        try:
            if getattr(self, 'winfo_exists', lambda: False)() and not getattr(self, '_shutdown', False):
                aft = getattr(self, 'after', None)
                if callable(aft):
                    aft(0, _upd)
                else:
                    _upd()
        except Exception:
            pass

    def add_notification(self, message):
        # Schedule adding the notification and updating the badge on the main thread
        def _add():
            try:
                self.notifications.append(message)
                self.update_notif_badge()
            except Exception:
                pass
        try:
            if getattr(self, 'winfo_exists', lambda: False)() and not getattr(self, '_shutdown', False):
                aft = getattr(self, 'after', None)
                if callable(aft):
                    aft(0, _add)
                else:
                    _add()
        except Exception:
            pass

    def clear_notifications(self, popup=None):
        self.notifications.clear()
        self.update_notif_badge()
        if popup:
            popup.destroy()
        messagebox.showinfo("Notifications", "All notifications cleared.")

    # --- User settings ---
    def show_user_settings(self):
        user = self.user
        top = tk.Toplevel(self)
        top.title("User Settings")
        tk.Label(top, text=f"Username: {user.get('username','')}", font=("Segoe UI", 12, "bold")).pack(pady=6)
        tk.Label(top, text=f"Role: {user.get('role','user')}", font=("Segoe UI", 10)).pack(pady=2)
        email_var = tk.StringVar(value=user.get("email", ""))
        tk.Label(top, text="Email:").pack()
        email_entry = tb.Entry(top, textvariable=email_var, width=30)
        email_entry.pack(pady=2)
        notif_pref_var = tk.BooleanVar(value=bool(user.get("notifications", True)))
        tb.Checkbutton(top, text="Enable Notifications", variable=notif_pref_var, style="info.TCheckbutton").pack(pady=2)
        tb.Button(top, text="Save", style="success.TButton", command=lambda: self.save_user_settings(email_var.get(), notif_pref_var.get(), top)).pack(pady=8)
        tb.Button(top, text="Close", style="secondary.TButton", command=top.destroy).pack(pady=2)

    def save_user_settings(self, email, notif_enabled, popup):
        self.user["email"] = email
        self.user["notifications"] = notif_enabled
        popup.destroy()
        messagebox.showinfo("Settings", "Settings saved! (stub, integrate with backend to persist changes)")

    # --- Admin user management (stub) ---
    def show_user_management(self):
        top = tk.Toplevel(self)
        top.title("User Management")
        tk.Label(top, text="(Admin) User Management - Coming Soon!", font=("Segoe UI", 12, "bold")).pack(pady=20)
        tb.Button(top, text="Close", style="secondary.TButton", command=top.destroy).pack(pady=15)

    # --- Admin: Send system alert (notification to all) ---
    def send_system_alert(self):
        alert = simpledialog.askstring("Send System Alert", "Enter alert message:")
        if alert:
            # In a real app, broadcast to all users via backend or socket
            try:
                # use central notifications dispatcher
                from notifications import notify
                notify('alert', alert)
            except Exception:
                # fallback to local enqueue
                self.backend_event_notification("ALERT", alert)
            messagebox.showinfo("Alert", "System alert sent. (stub, integrate with backend for global notification)")

    # --- Backend event hook for notifications ---
    def backend_event_notification(self, event_type, message):
        if self.user.get("notifications", True):
            # Ensure notifications are enqueued on the main thread
            self.add_notification(f"[{event_type.upper()}] {message}")

    # --- Update API quota (simulate) ---
    def update_api_quota(self, used=1):
        self.api_quota = max(0, self.api_quota - used)
        self.api_quota_label.config(text=f"API Quota: {self.api_quota}")

    # --- Refresh data (stub for triggering sync or polling backend) ---
    def refresh_data(self):
        self.sync_label.config(text="🔄 Syncing...")
        # Simulate data refresh from backend
        self.after(2000, lambda: self.sync_label.config(text="✅ Synced"))

    # --- Live backend integration: socket.io for notifications ---
    def start_socket_listener(self):
        # If socketio is not available in the environment, update UI and skip starting listener
        if not _HAS_SOCKETIO:
            try:
                self.sync_label.after(0, lambda: self.sync_label.config(text="⚠ Socket not available"))
            except Exception:
                pass
            return

        def listen():
            try:
                # import socketio lazily so static analyzers don't flag top-level None
                try:
                    import socketio as _socketio
                except Exception:
                    self.sync_label.after(0, lambda: self.sync_label.config(text="⚠ Socket not available"))
                    return

                self.socketio_client = _socketio.Client()

                @self.socketio_client.event
                def connect():
                    self.socket_connected = True
                    # Marshal to main thread
                    try:
                        self.sync_label.after(0, lambda: self.sync_label.config(text="🟢 Live Sync"))
                    except Exception:
                        pass

                @self.socketio_client.event
                def disconnect():
                    self.socket_connected = False
                    try:
                        self.sync_label.after(0, lambda: self.sync_label.config(text="🔴 Disconnected"))
                    except Exception:
                        pass

                @self.socketio_client.event
                def notification(data):
                    msg = data.get("msg", "New backend event")
                    event_type = data.get("type", "info")
                    self.backend_event_notification(event_type, msg)

                self.socketio_client.connect(self.backend_url)
                self.socketio_client.wait()
            except Exception as e:
                try:
                    # schedule UI update on main thread
                    if getattr(self, 'winfo_exists', lambda: False)():
                        aft = getattr(self, 'after', None)
                        if callable(aft):
                            try:
                                aft(0, lambda: self.sync_label.config(text="⚠️ Socket Error"))
                            except Exception:
                                try:
                                    self.sync_label.config(text="⚠️ Socket Error")
                                except Exception:
                                    pass
                        else:
                            try:
                                self.sync_label.config(text="⚠️ Socket Error")
                            except Exception:
                                pass
                except Exception:
                    pass
                # enqueue a notification safely
                try:
                    self.add_notification(f"[SOCKET ERROR] {e}")
                except Exception:
                    pass
        self.socket_thread = threading.Thread(target=listen, daemon=True)
        self.socket_thread.start()