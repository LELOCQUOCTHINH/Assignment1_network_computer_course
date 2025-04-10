import tkinter as tk
from tkinter import messagebox, ttk

class AfterLoginUI:
    def __init__(self, mode, identifier, conn):
        self.mode = mode  # "visitor" or "authenticated"
        self.identifier = identifier  # Name for visitor, username for authenticated
        self.conn = conn  # Socket connection to the server
        self.status = "Online" if mode == "authenticated" else "N/A"  # Default status

        self.root = tk.Tk()
        self.root.title(f"Welcome {self.identifier}")
        self.root.geometry("400x300")
        self.root.configure(bg="#f0f0f0")

        # Status bar frame (top-right corner)
        self.status_frame = tk.Frame(self.root, bg="#f0f0f0")
        self.status_frame.pack(side=tk.TOP, anchor="ne", padx=10, pady=5)

        # Status dot (canvas for circular dot)
        self.dot_canvas = tk.Canvas(self.status_frame, width=20, height=20, bg="#f0f0f0", highlightthickness=0)
        self.dot = self.dot_canvas.create_oval(5, 5, 15, 15, fill=self.get_status_color())
        self.dot_canvas.pack(side=tk.LEFT)

        # Status label
        self.status_label = tk.Label(self.status_frame, text=f"Status: {self.status}", font=("Arial", 10), bg="#f0f0f0", fg="#333")
        self.status_label.pack(side=tk.LEFT, padx=5)

        # Status dropdown (for authenticated users only)
        if self.mode == "authenticated":
            self.status_var = tk.StringVar(value=self.status)
            self.status_dropdown = ttk.Combobox(self.status_frame, textvariable=self.status_var, values=["Online", "Invisible"], state="readonly", width=10)
            self.status_dropdown.pack(side=tk.LEFT, padx=5)
            self.status_dropdown.bind("<<ComboboxSelected>>", self.update_status)

        # Welcome label
        welcome_text = f"Welcome, {self.identifier}!\nYou are logged in as {self.mode}."
        self.welcome_label = tk.Label(self.root, text=welcome_text, font=("Arial", 14, "bold"), bg="#f0f0f0", fg="#333")
        self.welcome_label.pack(pady=20)

        # Placeholder for channel manipulation
        self.info_label = tk.Label(self.root, text="Channel features coming soon!", bg="#f0f0f0", font=("Arial", 10))
        self.info_label.pack(pady=10)

        # Exit button to close the window
        self.exit_btn = tk.Button(self.root, text="Exit", command=self.close, width=10, bg="#FF4444", fg="white", font=("Arial", 10))
        self.exit_btn.pack(pady=20)

        self.root.mainloop()

    def get_status_color(self):
        """Return the color for the status dot."""
        if self.mode == "visitor":
            return "gray"  # Visitors don't have a status
        if self.status == "Online":
            return "green"
        elif self.status == "Invisible":
            return "black"
        else:  # Offline (not used here since user is connected)
            return "red"

    def update_status(self, event=None):
        """Update the user's status and notify the server."""
        new_status = self.status_var.get()
        if new_status != self.status:
            self.status = new_status
            self.status_label.config(text=f"Status: {self.status}")
            self.dot_canvas.itemconfig(self.dot, fill=self.get_status_color())
            # Send status update to server
            self.conn.sendall(f"SET_STATUS {self.identifier} {self.status}".encode())
            response = self.conn.recv(1024).decode()
            if response != "STATUS_UPDATED":
                messagebox.showerror("Error", "Failed to update status on server.")
                self.status_var.set(self.status)  # Revert on failure

    def close(self):
        """Close the UI and the socket connection."""
        if self.mode == "authenticated":
            # Set status to Offline before closing
            self.conn.sendall(f"SET_STATUS {self.identifier} Offline".encode())
            self.conn.recv(1024)  # Wait for acknowledgment (discard response)
        self.conn.close()
        self.root.destroy()