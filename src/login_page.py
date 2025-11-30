import tkinter as tk
import ttkbootstrap as tb
from tkinter import messagebox

# Simple user store (replace with DB for production)

import hashlib
from db_handler import DBHandler

class LoginPage(tb.Frame):
    def __init__(self, parent, on_login):
        super().__init__(parent)
        self.parent = parent
        self.on_login = on_login
        self.pack(fill="both", expand=True)
        main = tb.Frame(self)
        main.pack(expand=True)

        tb.Label(main, text="Login", font=("Segoe UI", 18, "bold"), foreground="#0984e3").pack(pady=(24,12))
        tb.Label(main, text="Username:", font=("Segoe UI", 12)).pack(anchor="w", padx=18)
        self.username_var = tk.StringVar()
        tb.Entry(main, textvariable=self.username_var, width=24).pack(padx=18, pady=4)
        tb.Label(main, text="Password:", font=("Segoe UI", 12)).pack(anchor="w", padx=18)
        self.password_var = tk.StringVar()
        tb.Entry(main, textvariable=self.password_var, show="*", width=24).pack(padx=18, pady=4)
        tb.Button(main, text="Login", width=18, command=self.try_login, style="success.TButton").pack(pady=16)
        tb.Button(main, text="Register", width=18, command=self.show_register, style="info.TButton").pack(pady=4)
        self.error_label = tb.Label(main, text="", font=("Segoe UI", 10), foreground="#d63031")
        self.error_label.pack()

    def hash_password(self, password):
        return hashlib.sha256(password.encode()).hexdigest()

    def try_login(self):
        username = self.username_var.get().strip()
        password = self.password_var.get().strip()
        with DBHandler() as db:
            user = db.fetch_one("SELECT password_hash, role FROM users WHERE username=?", (username,))
        if user and user[0] == self.hash_password(password):
            self.error_label.config(text="")
            self.on_login(username)
        else:
            self.error_label.config(text="Invalid username or password.")
            self.password_var.set("")

    def show_register(self):
        RegisterDialog(self)

class RegisterDialog(tk.Toplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.title("Register New User")
        self.geometry("340x220")
        self.resizable(False, False)
        self.parent = parent
        self.protocol("WM_DELETE_WINDOW", self.destroy)
        self.build_form()

    def build_form(self):
        frame = tb.Frame(self)
        frame.pack(expand=True, padx=18, pady=18)
        tb.Label(frame, text="Username:", font=("Segoe UI", 11)).grid(row=0, column=0, sticky="w")
        self.username_var = tk.StringVar()
        tb.Entry(frame, textvariable=self.username_var, width=22).grid(row=0, column=1, pady=6)
        tb.Label(frame, text="Password:", font=("Segoe UI", 11)).grid(row=1, column=0, sticky="w")
        self.password_var = tk.StringVar()
        tb.Entry(frame, textvariable=self.password_var, show="*", width=22).grid(row=1, column=1, pady=6)
        tb.Label(frame, text="Role:", font=("Segoe UI", 11)).grid(row=2, column=0, sticky="w")
        self.role_var = tk.StringVar(value="user")
        tb.Combobox(frame, values=["user", "admin"], textvariable=self.role_var, state="readonly", width=20).grid(row=2, column=1, pady=6)
        tb.Button(frame, text="Register", width=16, command=self.register_user, style="success.TButton").grid(row=3, column=0, columnspan=2, pady=12)
        self.error_label = tb.Label(frame, text="", font=("Segoe UI", 10), foreground="#d63031")
        self.error_label.grid(row=4, column=0, columnspan=2)

    def hash_password(self, password):
        import hashlib
        return hashlib.sha256(password.encode()).hexdigest()

    def register_user(self):
        username = self.username_var.get().strip()
        password = self.password_var.get().strip()
        role = self.role_var.get()
        if not username or not password:
            self.error_label.config(text="Username and password required.")
            return
        with DBHandler() as db:
            exists = db.fetch_one("SELECT id FROM users WHERE username=?", (username,))
            if exists:
                self.error_label.config(text="Username already exists.")
                return
            db.execute_query("INSERT INTO users (username, password_hash, role) VALUES (?, ?, ?)", (username, self.hash_password(password), role))
        self.error_label.config(text="User registered! You can now log in.")
        self.after(1200, self.destroy)
