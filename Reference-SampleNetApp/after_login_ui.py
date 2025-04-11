import tkinter as tk
from tkinter import messagebox, ttk
from tkinter import Canvas, Scrollbar

class AfterLoginUI:
    def __init__(self, mode, identifier, conn):
        self.mode = mode  # "visitor" or "authenticated"
        self.identifier = identifier  # Name for visitor, username for authenticated
        self.conn = conn  # Socket connection to the server
        self.status = "Online" if mode == "authenticated" else "N/A"  # Default status

        # Print statement: Log initialization details
        print(f"[AfterLoginUI] Initializing UI for user: {self.identifier}, mode: {self.mode}, initial status: {self.status}")

        # Colors (Discord-inspired)
        self.bg_color = "#7289da"  # Main background (purple-blue)
        self.sidebar_color = "#2f3136"  # Sidebar background (dark gray)
        self.main_color = "#36393f"  # Main area background (slightly lighter gray)
        self.text_color = "#dcddde"  # Text color (light gray/white)
        self.logout_btn_color = "#FF4444"  # Logout button color (red)
        self.create_btn_color = "#7289da"  # Create button color (same as main background for consistency)

        # Create the main window
        self.root = tk.Tk()
        self.root.title(f"Chat App - {self.identifier}")
        self.root.geometry("800x600")
        self.root.configure(bg=self.bg_color)

        # Bind the close method to the window close event
        self.root.protocol("WM_DELETE_WINDOW", self.close)

        # Main frame to hold sidebar and main area
        self.main_frame = tk.Frame(self.root, bg=self.bg_color)
        self.main_frame.pack(fill="both", expand=True)

        # Sidebar (left side)
        self.sidebar_frame = tk.Frame(self.main_frame, bg=self.sidebar_color, width=200)
        self.sidebar_frame.pack(side="left", fill="y")
        self.sidebar_frame.pack_propagate(False)  # Prevent sidebar from resizing

        # Section 1: Hosting Channels
        self.hosting_frame = tk.Frame(self.sidebar_frame, bg=self.sidebar_color, height=166)
        self.hosting_frame.pack(fill="x")
        self.hosting_frame.pack_propagate(False)  # Enforce fixed height
        self.create_channel_section("Hosting channels", self.hosting_frame, is_hosting=True)

        # Section 2: Joining Channels
        self.joining_frame = tk.Frame(self.sidebar_frame, bg=self.sidebar_color, height=166)
        self.joining_frame.pack(fill="x")
        self.joining_frame.pack_propagate(False)  # Enforce fixed height
        self.create_channel_section("Joining channels", self.joining_frame)

        # Section 3: Other Channels
        self.other_frame = tk.Frame(self.sidebar_frame, bg=self.sidebar_color, height=166)
        self.other_frame.pack(fill="x")
        self.other_frame.pack_propagate(False)  # Enforce fixed height
        self.create_channel_section("Other channels", self.other_frame)

        # Section 4: User Bar
        self.user_bar_section = tk.Frame(self.sidebar_frame, bg=self.sidebar_color, height=100)
        self.user_bar_section.pack(side="bottom", fill="x")
        self.user_bar_section.pack_propagate(False)  # Enforce fixed height

        # User bar inside the user_bar_section
        self.user_bar_frame = tk.Frame(self.user_bar_section, bg=self.sidebar_color)
        self.user_bar_frame.pack(fill="x", padx=5, pady=5)

        # User name label
        self.user_label = tk.Label(self.user_bar_frame, text=self.identifier, font=("Arial", 10), bg=self.sidebar_color, fg=self.text_color)
        self.user_label.pack(anchor="w", pady=2)

        # Status frame
        self.status_frame = tk.Frame(self.user_bar_frame, bg=self.sidebar_color)
        self.status_frame.pack(fill="x", pady=2)

        # Status dot (canvas for circular dot)
        self.dot_canvas = tk.Canvas(self.status_frame, width=20, height=20, bg=self.sidebar_color, highlightthickness=0)
        self.dot = self.dot_canvas.create_oval(5, 5, 15, 15, fill=self.get_status_color())
        self.dot_canvas.pack(side="left")

        # Status label
        self.status_label = tk.Label(self.status_frame, text=f"Status: {self.status}", font=("Arial", 10), bg=self.sidebar_color, fg=self.text_color)
        self.status_label.pack(side="left", padx=5)

        # Status dropdown (for authenticated users only)
        if self.mode == "authenticated":
            self.status_var = tk.StringVar(value=self.status)
            self.status_dropdown = ttk.Combobox(self.status_frame, textvariable=self.status_var, values=["Online", "Invisible"], state="readonly", width=10)
            self.status_dropdown.pack(side="left", padx=5)
            self.status_dropdown.bind("<<ComboboxSelected>>", self.update_status)

        # Logout button
        self.logout_btn = tk.Button(self.user_bar_frame, text="LOGOUT", command=self.close, width=10, bg=self.logout_btn_color, fg="white", font=("Arial", 10))
        self.logout_btn.pack(anchor="w", pady=5)

        # Main area (right side)
        self.content_frame = tk.Frame(self.main_frame, bg=self.main_color)
        self.content_frame.pack(side="right", fill="both", expand=True)

        # Welcome message in the main area
        welcome_text = f"WELCOME, {self.identifier}!\nYou are logged in as {self.mode}."
        self.welcome_label = tk.Label(self.content_frame, text=welcome_text, font=("Arial", 16, "bold"), bg=self.main_color, fg=self.text_color)
        self.welcome_label.pack(pady=50)

        # Placeholder for chat area
        self.chat_placeholder = tk.Label(self.content_frame, text="Chat features coming soon!", font=("Arial", 12), bg=self.main_color, fg=self.text_color)
        self.chat_placeholder.pack(pady=10)

        self.root.mainloop()

    def create_channel_section(self, title, parent_frame, is_hosting=False):
        """Create a channel section with an optional 'Create a New Channel' button."""
        # Print statement: Log channel section creation
        print(f"[AfterLoginUI] Creating channel section: {title}, is_hosting: {is_hosting}")

        # Section frame
        section_frame = tk.Frame(parent_frame, bg=self.sidebar_color)
        section_frame.pack(fill="both", expand=True, padx=5, pady=5)

        # Add "Create a New Channel" button before the title for Hosting channels
        if is_hosting:
            create_btn = tk.Button(section_frame, text="Create a New Channel", command=self.on_create_channel,
                                   bg=self.create_btn_color, fg="white", font=("Arial", 10))
            create_btn.pack(anchor="w", padx=5, pady=2)
            print(f"[AfterLoginUI] Added 'Create a New Channel' button to {title} section")

        # Section title
        title_label = tk.Label(section_frame, text=title, font=("Arial", 12, "bold"), bg=self.sidebar_color, fg=self.text_color)
        title_label.pack(anchor="w", padx=5)

        # Scrollable frame for channels
        canvas = Canvas(section_frame, bg=self.sidebar_color, highlightthickness=0)
        scrollbar = ttk.Scrollbar(section_frame, orient="vertical", command=canvas.yview, style="Vertical.TScrollbar")
        scrollable_frame = tk.Frame(canvas, bg=self.sidebar_color)

        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )

        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        # Pack the scrollbar and canvas
        scrollbar.pack(side="left", fill="y")
        canvas.pack(side="left", fill="both", expand=True)

        # Add channels (10 channels to test scrollbar)
        for i in range(10):
            channel_label = tk.Label(scrollable_frame, text=f"Channel {i+1}", font=("Arial", 10), bg=self.sidebar_color, fg=self.text_color)
            channel_label.pack(anchor="w", padx=10, pady=2)

        # Customize scrollbar style to match dark theme
        style = ttk.Style()
        style.configure("Vertical.TScrollbar", background="#444444", troughcolor="#333333", borderwidth=0)

    def on_create_channel(self):
        """Handle the 'Create a New Channel' button click."""
        # Print statement: Log button click
        print(f"[AfterLoginUI] 'Create a New Channel' button clicked by user: {self.identifier}")
        messagebox.showinfo("Info", "Create a New Channel clicked! Functionality to be implemented.")
        # Future: Add logic to create a channel here

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
            # Print statement: Log status change attempt
            print(f"[AfterLoginUI] User {self.identifier} attempting to change status from {self.status} to {new_status}")
            try:
                self.conn.sendall(f"SET_STATUS {self.identifier} {new_status}".encode())
                response = self.conn.recv(1024).decode()
                if response != "STATUS_UPDATED":
                    messagebox.showerror("Error", "Failed to update status on server.")
                    self.status_var.set(self.status)
                    print(f"[AfterLoginUI] Status update failed for {self.identifier}: {response}")
                else:
                    self.status = new_status
                    self.status_label.config(text=f"Status: {self.status}")
                    self.dot_canvas.itemconfig(self.dot, fill=self.get_status_color())
                    print(f"[AfterLoginUI] Status updated successfully for {self.identifier}: {self.status}")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to communicate with server: {e}")
                self.status_var.set(self.status)
                print(f"[AfterLoginUI] Status update error for {self.identifier}: {e}")

    def close(self):
        """Close the UI and the socket connection."""
        # Print statement: Log close/logout attempt
        print(f"[AfterLoginUI] Closing UI for user: {self.identifier}, mode: {self.mode}")
        if self.mode == "authenticated":
            try:
                # Query the current status
                self.conn.sendall(f"GET_STATUS {self.identifier}".encode())
                response = self.conn.recv(1024).decode()
                if response.startswith("STATUS"):
                    current_status = response.split()[1]
                    print(f"[AfterLoginUI] Current status for {self.identifier}: {current_status}")
                    # Only set status to Offline if not Invisible
                    if current_status != "Invisible":
                        self.conn.sendall(f"SET_STATUS {self.identifier} Offline".encode())
                        self.conn.recv(1024)  # Wait for acknowledgment (discard response)
                        print(f"[AfterLoginUI] Set status to Offline for {self.identifier}")
            except Exception as e:
                print(f"[AfterLoginUI] Error during logout status update for {self.identifier}: {e}")
            finally:
                self.conn.close()
                print(f"[AfterLoginUI] Socket connection closed for {self.identifier}")
        self.root.destroy()
        print(f"[AfterLoginUI] UI destroyed for {self.identifier}")