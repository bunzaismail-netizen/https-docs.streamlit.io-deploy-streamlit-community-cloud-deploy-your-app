import tkinter as tk
import ttkbootstrap as tb
from tkinter import messagebox, simpledialog, filedialog
from db_handler import DBHandler

class UserManagementPage(tb.Frame):
    def __init__(self, parent, user, *args, **kwargs):
        super().__init__(parent, *args, **kwargs)
        self.user = user
        self.page = 1
        self.page_size = 20
        self.total_users = 0
    # Do not pack here; main app controls page layout via show_page
        self.create_widgets()
        self.refresh_users()

    def create_widgets(self):
        title = tk.Label(self, text="User Management", font=("Segoe UI", 16, "bold"))
        title.pack(pady=10)
        # Search/filter and sort controls
        control_frame = tk.Frame(self)
        control_frame.pack(pady=4)
        tk.Label(control_frame, text="Search:").pack(side="left")
        self.search_var = tk.StringVar()
        search_entry = tk.Entry(control_frame, textvariable=self.search_var, width=16)
        search_entry.pack(side="left", padx=4)
        search_entry.bind("<Return>", lambda e: self.refresh_users())
        tk.Label(control_frame, text="Sort by:").pack(side="left", padx=(12,0))
        self.sort_var = tk.StringVar(value="username")
        sort_menu = tk.OptionMenu(control_frame, self.sort_var, "username", "role", "id", command=lambda _: self.refresh_users())
        sort_menu.pack(side="left", padx=4)
        self.order_var = tk.StringVar(value="asc")
        order_menu = tk.OptionMenu(control_frame, self.order_var, "asc", "desc", command=lambda _: self.refresh_users())
        order_menu.pack(side="left", padx=4)
        # User list
        # Use a Listbox with multiple selection for bulk actions
        self.user_listbox = tk.Listbox(self, width=60, height=12, selectmode=tk.MULTIPLE)
        self.user_listbox.pack(pady=8)
        # Pagination controls
        page_frame = tk.Frame(self)
        page_frame.pack(pady=2)
        self.prev_btn = tk.Button(page_frame, text="Prev", command=self.prev_page)
        self.prev_btn.pack(side="left", padx=4)
        self.page_label = tk.Label(page_frame, text="Page 1")
        self.page_label.pack(side="left", padx=4)
        self.next_btn = tk.Button(page_frame, text="Next", command=self.next_page)
        self.next_btn.pack(side="left", padx=4)
        # Action buttons
        btn_frame = tk.Frame(self)
        btn_frame.pack(pady=6)
        tk.Button(btn_frame, text="Add User", command=self.add_user).pack(side="left", padx=4)
        tk.Button(btn_frame, text="Edit User", command=self.edit_user).pack(side="left", padx=4)
        tk.Button(btn_frame, text="Delete User", command=self.delete_user).pack(side="left", padx=4)
        tk.Button(btn_frame, text="Delete Selected", command=self.delete_selected_users).pack(side="left", padx=4)
        tk.Button(btn_frame, text="Change Role for Selected", command=self.change_role_selected).pack(side="left", padx=4)
        tk.Button(btn_frame, text="Toggle Status", command=self.toggle_status_selected).pack(side="left", padx=4)
        tk.Button(btn_frame, text="Export to CSV", command=self.export_users_csv).pack(side="left", padx=4)
        tk.Button(btn_frame, text="View Audit Log", command=self.view_audit_log).pack(side="left", padx=4)
        tk.Button(btn_frame, text="Refresh", command=self.refresh_users).pack(side="left", padx=4)
    def delete_selected_users(self):
        selected = self.user_listbox.curselection()
        if not selected:
            messagebox.showinfo("Bulk Delete", "Select users to delete.")
            return
        ids = [int(self.user_listbox.get(i).split(":")[0]) for i in selected]
        from db_handler import DBHandler
        with DBHandler() as db:
            for user_id in ids:
                db.delete_user(user_id)
                db.log_audit("delete", f"User {user_id} deleted (bulk)")
        self.refresh_users()

    def change_role_selected(self):
        selected = self.user_listbox.curselection()
        if not selected:
            messagebox.showinfo("Bulk Role Change", "Select users to change role.")
            return
        role = simpledialog.askstring("Change Role", "Enter new role for selected users:")
        if not role:
            return
        ids = [int(self.user_listbox.get(i).split(":")[0]) for i in selected]
        from db_handler import DBHandler
        with DBHandler() as db:
            for user_id in ids:
                db.execute_query("UPDATE users SET role=? WHERE id=?", (role, user_id))
                db.log_audit("role_change", f"User {user_id} role changed to {role} (bulk)")
        self.refresh_users()

    def toggle_status_selected(self):
        selected = self.user_listbox.curselection()
        if not selected:
            messagebox.showinfo("Toggle Status", "Select users to toggle status.")
            return
        ids = [int(self.user_listbox.get(i).split(":")[0]) for i in selected]
        from db_handler import DBHandler
        with DBHandler() as db:
            for user_id in ids:
                # Get current status
                cursor = db.execute_query("SELECT status FROM users WHERE id=?", (user_id,))
                status = cursor.fetchone()[0] if cursor else "active"
                new_status = "inactive" if status == "active" else "active"
                db.set_user_status(user_id, new_status)
                db.log_audit("status_toggle", f"User {user_id} status changed to {new_status} (bulk)")
        self.refresh_users()

    def export_users_csv(self):
        from db_handler import DBHandler
        import csv
        file_path = filedialog.asksaveasfilename(title="Export Users to CSV", defaultextension=".csv", filetypes=[("CSV Files", "*.csv")])
        if not file_path:
            return
        search = self.search_var.get()
        sort = self.sort_var.get()
        order = self.order_var.get()
        offset = (self.page - 1) * self.page_size
        with DBHandler() as db:
            users = db.get_users(search=search, sort=sort, order=order, limit=self.page_size, offset=offset)
        with open(file_path, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["ID", "Username", "Role", "Status"])
            for u in users:
                writer.writerow([u["id"], u["username"], u["role"], u["status"]])
        messagebox.showinfo("Export", f"Users exported to {file_path}")

    def view_audit_log(self):
        import csv, os
        log_file = os.path.join(os.path.dirname(__file__), "..", "user_audit_log.csv")
        if not os.path.exists(log_file):
            messagebox.showinfo("Audit Log", "No audit log found.")
            return
        log_win = tk.Toplevel(self)
        log_win.title("User Audit Log")
        log_win.geometry("700x400")
        log_list = tk.Listbox(log_win, width=100, height=20)
        log_list.pack(pady=10)
        with open(log_file, "r") as f:
            reader = csv.reader(f)
            for row in reader:
                log_list.insert(tk.END, " | ".join(row))
        # Pagination state
        self.page = 1
        self.page_size = 20
        self.total_users = 0

    def refresh_users(self):
        self.user_listbox.delete(0, tk.END)
        search = self.search_var.get()
        sort = self.sort_var.get()
        order = self.order_var.get()
        offset = (self.page - 1) * self.page_size
        def load_users():
            from db_handler import DBHandler
            with DBHandler() as db:
                users = db.get_users(search=search, sort=sort, order=order, limit=self.page_size, offset=offset)
                # Get total count for pagination
                count_cursor = db.execute_query("SELECT COUNT(*) FROM users" + (f" WHERE username LIKE ? OR role LIKE ?" if search else ""), tuple([f"%{search}%", f"%{search}%"] if search else []))
                total = count_cursor.fetchone()[0] if count_cursor else 0
            def update_listbox():
                self.user_listbox.delete(0, tk.END)
                for u in users:
                    self.user_listbox.insert(tk.END, f"{u['id']}: {u['username']} ({u['role']}) - {u.get('email','')}")
                self.total_users = total
                total_pages = max(1, (self.total_users + self.page_size - 1) // self.page_size)
                self.page_label.config(text=f"Page {self.page} of {total_pages}")
                self.prev_btn.config(state="normal" if self.page > 1 else "disabled")
                self.next_btn.config(state="normal" if self.page < total_pages else "disabled")
            self.after(0, update_listbox)
        import threading
        threading.Thread(target=load_users, daemon=True).start()

    def next_page(self):
        total_pages = max(1, (self.total_users + self.page_size - 1) // self.page_size)
        if self.page < total_pages:
            self.page += 1
            self.refresh_users()

    def prev_page(self):
        if self.page > 1:
            self.page -= 1
            self.refresh_users()

    def add_user(self):
        from login_page import RegisterDialog
        dialog = RegisterDialog(self)
        self.wait_window(dialog)
        self.refresh_users()

    def edit_user(self):
        selection = self.user_listbox.curselection()
        if not selection:
            messagebox.showinfo("Edit User", "Select a user to edit.")
            return
        idx = selection[0]
        user_str = self.user_listbox.get(idx)
        user_id = int(user_str.split(":")[0])
        from edit_user_dialog import EditUserDialog
        dialog = EditUserDialog(self, user_id)
        self.wait_window(dialog)
        self.refresh_users()

    def delete_user(self):
        selection = self.user_listbox.curselection()
        if not selection:
            messagebox.showinfo("Delete User", "Select a user to delete.")
            return
        idx = selection[0]
        user_str = self.user_listbox.get(idx)
        user_id = int(user_str.split(":")[0])
        if messagebox.askyesno("Delete User", "Are you sure you want to delete this user?"):
            from db_handler import DBHandler
            with DBHandler() as db:
                db.delete_user(user_id)
            self.refresh_users()
