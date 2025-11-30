import tkinter as tk
import ttkbootstrap as tb
from tkinter import messagebox
from db_handler import DBHandler

class EditUserDialog(tk.Toplevel):
    def __init__(self, parent, user_id):
        super().__init__(parent)
        self.title("Edit User")
        self.geometry("340x240")
        self.resizable(False, False)
        self.user_id = user_id
        self.parent = parent
        self.protocol("WM_DELETE_WINDOW", self.destroy)
        self.build_form()
        self.load_user()

    def build_form(self):
        frame = tb.Frame(self)
        frame.pack(expand=True, padx=18, pady=18)
        tb.Label(frame, text="Username:", font=("Segoe UI", 11)).grid(row=0, column=0, sticky="w")
        self.username_var = tk.StringVar()
        tb.Entry(frame, textvariable=self.username_var, width=22).grid(row=0, column=1, pady=6)
        tb.Label(frame, text="Role:", font=("Segoe UI", 11)).grid(row=1, column=0, sticky="w")
        self.role_var = tk.StringVar(value="user")
        tb.Combobox(frame, values=["user", "admin"], textvariable=self.role_var, state="readonly", width=20).grid(row=1, column=1, pady=6)
        tb.Label(frame, text="Password (leave blank to keep):", font=("Segoe UI", 11)).grid(row=2, column=0, sticky="w")
        self.password_var = tk.StringVar()
        tb.Entry(frame, textvariable=self.password_var, show="*", width=22).grid(row=2, column=1, pady=6)
        tb.Button(frame, text="Save Changes", width=16, command=self.save_user, style="success.TButton").grid(row=3, column=0, columnspan=2, pady=12)
        self.error_label = tb.Label(frame, text="", font=("Segoe UI", 10), foreground="#d63031")
        self.error_label.grid(row=4, column=0, columnspan=2)

    def load_user(self):
        with DBHandler() as db:
            user = db.fetch_one("SELECT username, role FROM users WHERE id=?", (self.user_id,))
        if user:
            self.username_var.set(user[0])
            self.role_var.set(user[1])
        else:
            self.error_label.config(text="User not found.")

    def save_user(self):
        username = self.username_var.get().strip()
        role = self.role_var.get()
        password = self.password_var.get().strip()
        if not username:
            self.error_label.config(text="Username required.")
            return
        with DBHandler() as db:
            # Check for username conflict
            existing = db.fetch_one("SELECT id FROM users WHERE username=? AND id<>?", (username, self.user_id))
            if existing:
                self.error_label.config(text="Username already exists.")
                return
            if password:
                import hashlib
                password_hash = hashlib.sha256(password.encode()).hexdigest()
                db.execute_query("UPDATE users SET username=?, role=?, password_hash=? WHERE id=?", (username, role, password_hash, self.user_id))
            else:
                db.execute_query("UPDATE users SET username=?, role=? WHERE id=?", (username, role, self.user_id))
        self.error_label.config(text="User updated!")
        self.after(1200, self.destroy)
