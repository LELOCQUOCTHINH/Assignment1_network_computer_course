import tkinter as tk
from tkinter import messagebox

class LoginUI:
    def __init__(self, conn, on_complete):
        self.conn = conn  # Socket connection to the server
        self.on_complete = on_complete  # Callback to proceed after login
        self.root = tk.Tk()
        self.root.title("Segment Chat Login")
        self.root.geometry("400x300")
        self.root.configure(bg="#f0f0f0")

        # Welcome label
        self.welcome_label = tk.Label(self.root, text="Welcome to Segment Chat!", font=("Arial", 14, "bold"), bg="#f0f0f0", fg="#333")
        self.welcome_label.pack(pady=20)

        # Buttons for mode selection
        self.visitor_btn = tk.Button(self.root, text="Continue as Visitor", command=self.visitor_mode, width=20, bg="#4CAF50", fg="white", font=("Arial", 10))
        self.visitor_btn.pack(pady=5)

        self.login_btn = tk.Button(self.root, text="Log In", command=self.login_mode, width=20, bg="#2196F3", fg="white", font=("Arial", 10))
        self.login_btn.pack(pady=5)

        self.register_btn = tk.Button(self.root, text="Register", command=self.register_mode, width=20, bg="#FF9800", fg="white", font=("Arial", 10))
        self.register_btn.pack(pady=5)

        self.root.mainloop()

    def send_command(self, command):
        """Send a command to the server and get response."""
        self.conn.sendall(command.encode())
        return self.conn.recv(1024).decode()

    def visitor_mode(self):
        """Handle Visitor mode in a new window."""
        visitor_window = tk.Toplevel(self.root)
        visitor_window.title("Visitor Mode")
        visitor_window.geometry("300x200")
        visitor_window.configure(bg="#f0f0f0")

        tk.Label(visitor_window, text="Enter your name:", bg="#f0f0f0", font=("Arial", 12)).pack(pady=10)
        name_entry = tk.Entry(visitor_window, width=25)
        name_entry.pack(pady=5)

        def submit_visitor():
            name = name_entry.get().strip()
            if name:
                response = self.send_command(f"VISITOR {name}")
                if response.startswith("WELCOME_VISITOR"):
                    messagebox.showinfo("Success", f"Welcome, {name}!")
                    visitor_window.destroy()
                    self.root.destroy()
                    self.on_complete("visitor", name)
                else:
                    messagebox.showerror("Error", response)
            else:
                messagebox.showwarning("Warning", "Please enter a name.")

        tk.Button(visitor_window, text="Submit", command=submit_visitor, bg="#4CAF50", fg="white").pack(pady=10)

    def login_mode(self):
        """Handle Login mode in a new window."""
        login_window = tk.Toplevel(self.root)
        login_window.title("Log In")
        login_window.geometry("300x250")
        login_window.configure(bg="#f0f0f0")

        tk.Label(login_window, text="Username:", bg="#f0f0f0", font=("Arial", 12)).pack(pady=5)
        username_entry = tk.Entry(login_window, width=25)
        username_entry.pack(pady=5)

        tk.Label(login_window, text="Password:", bg="#f0f0f0", font=("Arial", 12)).pack(pady=5)
        password_entry = tk.Entry(login_window, width=25, show="*")
        password_entry.pack(pady=5)

        def submit_login():
            username = username_entry.get().strip()
            password = password_entry.get().strip()
            if username and password:
                response = self.send_command(f"LOGIN {username} {password}")
                if response.startswith("LOGIN_SUCCESS"):
                    messagebox.showinfo("Success", "Login successful!")
                    login_window.destroy()
                    self.root.destroy()
                    self.on_complete("authenticated", username)
                else:
                    messagebox.showerror("Error", "Login failed: " + response)
            else:
                messagebox.showwarning("Warning", "Please fill in all fields.")

        tk.Button(login_window, text="Log In", command=submit_login, bg="#2196F3", fg="white").pack(pady=10)

    def register_mode(self):
        """Handle Registration mode in a new window."""
        register_window = tk.Toplevel(self.root)
        register_window.title("Register")
        register_window.geometry("300x300")
        register_window.configure(bg="#f0f0f0")

        tk.Label(register_window, text="Username:", bg="#f0f0f0", font=("Arial", 12)).pack(pady=5)
        username_entry = tk.Entry(register_window, width=25)
        username_entry.pack(pady=5)

        tk.Label(register_window, text="Password:", bg="#f0f0f0", font=("Arial", 12)).pack(pady=5)
        password_entry = tk.Entry(register_window, width=25, show="*")
        password_entry.pack(pady=5)

        tk.Label(register_window, text="Confirm Password:", bg="#f0f0f0", font=("Arial", 12)).pack(pady=5)
        confirm_entry = tk.Entry(register_window, width=25, show="*")
        confirm_entry.pack(pady=5)

        def submit_register():
            username = username_entry.get().strip()
            password = password_entry.get().strip()
            confirm = confirm_entry.get().strip()
            if not (username and password and confirm):
                messagebox.showwarning("Warning", "Please fill in all fields.")
                return
            if password != confirm:
                messagebox.showerror("Error", "Passwords do not match.")
                return
            response = self.send_command(f"REGISTER {username} {password}")
            if response.startswith("REGISTER_SUCCESS"):
                messagebox.showinfo("Success", "Registration successful! Please log in.")
                register_window.destroy()
            else:
                messagebox.showerror("Error", "Registration failed: " + response)

        tk.Button(register_window, text="Register", command=submit_register, bg="#FF9800", fg="white").pack(pady=10)