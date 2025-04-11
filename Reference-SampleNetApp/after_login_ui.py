import tkinter as tk
from tkinter import messagebox, ttk
from tkinter import Canvas, Scrollbar
import threading
import socket

class AfterLoginUI:
    def __init__(self, mode, identifier, user_id, conn):
        self.mode = mode  # "visitor" or "authenticated"
        self.identifier = identifier  # Username (for display)
        self.user_id = user_id  # Unique user ID
        self.conn = conn  # Socket connection to the server
        self.status = "Online" if mode == "authenticated" else "N/A"  # Default status

        # Set a timeout on the socket to prevent blocking in the listener thread
        self.conn.settimeout(1.0)  # 1-second timeout for recv calls

        # Channel data (channel_id: {"name": name, "host": user_id, "members": [user_ids]})
        self.channels = {}
        self.selected_channel_id = None  # Track the currently selected channel

        # Print statement: Log initialization details
        print(f"[AfterLoginUI] Initializing UI for user: {self.identifier} (ID: {self.user_id}), mode: {self.mode}, initial status: {self.status}")

        # Colors (Discord-inspired)
        self.bg_color = "#7289da"
        self.sidebar_color = "#2f3136"
        self.main_color = "#36393f"
        self.text_color = "#dcddde"
        self.logout_btn_color = "#FF4444"
        self.create_btn_color = "#7289da"
        self.join_btn_color = "#4CAF50"  # Green for Join button

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
        self.sidebar_frame.pack_propagate(False)

        # Section 1: Hosting Channels
        self.hosting_frame = tk.Frame(self.sidebar_frame, bg=self.sidebar_color, height=166)
        self.hosting_frame.pack(fill="x")
        self.hosting_frame.pack_propagate(False)
        self.hosting_channels_frame = None  # Will hold the scrollable frame
        self.create_channel_section("Hosting channels", self.hosting_frame, is_hosting=True)

        # Section 2: Joining Channels
        self.joining_frame = tk.Frame(self.sidebar_frame, bg=self.sidebar_color, height=166)
        self.joining_frame.pack(fill="x")
        self.joining_frame.pack_propagate(False)
        self.joining_channels_frame = None  # Will hold the scrollable frame
        self.create_channel_section("Joining channels", self.joining_frame)

        # Section 3: Other Channels
        self.other_frame = tk.Frame(self.sidebar_frame, bg=self.sidebar_color, height=166)
        self.other_frame.pack(fill="x")
        self.other_frame.pack_propagate(False)
        self.other_channels_frame = None  # Will hold the scrollable frame
        self.create_channel_section("Other channels", self.other_frame)

        # Section 4: User Bar
        self.user_bar_section = tk.Frame(self.sidebar_frame, bg=self.sidebar_color, height=100)
        self.user_bar_section.pack(side="bottom", fill="x")
        self.user_bar_section.pack_propagate(False)

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

        # Welcome message in the main area (initial state)
        self.welcome_label = tk.Label(self.content_frame, text=f"WELCOME, {self.identifier}!\nYou are logged in as {self.mode}.", font=("Arial", 16, "bold"), bg=self.main_color, fg=self.text_color)
        self.welcome_label.pack(pady=50)

        # Placeholder for chat area (initial state)
        self.chat_placeholder = tk.Label(self.content_frame, text="Chat features coming soon!", font=("Arial", 12), bg=self.main_color, fg=self.text_color)
        self.chat_placeholder.pack(pady=10)

        # Start a thread to listen for server updates
        self.running = True
        self.listener_thread = threading.Thread(target=self.listen_for_updates)
        self.listener_thread.start()

        # Fetch initial channel list from the server
        self.fetch_channels()

        self.root.mainloop()

    def fetch_channels(self):
        """Fetch the initial list of channels from the server."""
        try:
            self.conn.sendall("GET_CHANNELS".encode())
        except Exception as e:
            print(f"[AfterLoginUI] Error fetching channels for {self.identifier} (ID: {self.user_id}): {e}")

    def listen_for_updates(self):
        """Listen for updates from the server (e.g., new channels, joined channels)."""
        while self.running:
            try:
                data = self.conn.recv(1024).decode()
                if not data:
                    break
                print(f"[AfterLoginUI] Received update for {self.identifier} (ID: {self.user_id}): {data}")
                # Handle multiple messages separated by newlines
                messages = data.split("\n")
                for message in messages:
                    if not message:
                        continue
                    command = message.split()

                    if command[0] == "NO_CHANNELS":
                        self.channels = {}
                        self.update_channel_lists()

                    elif command[0] == "CHANNEL":
                        channel_id = int(command[1])
                        channel_name = " ".join(command[2:command.index(command[3])])
                        host = command[command.index(command[3])]
                        members = command[command.index(command[3]) + 1:]
                        self.channels[channel_id] = {
                            "name": channel_name,
                            "host": host,
                            "members": members
                        }
                        self.update_channel_lists()

                    elif command[0] == "UPDATE_CHANNELS":
                        channel_id = int(command[1])
                        channel_name = " ".join(command[2:command.index(command[3])])
                        host = command[3]
                        # Fetch the updated channel list
                        self.fetch_channels()

                    elif command[0] == "CHANNEL_CREATED":
                        channel_id = int(command[1])
                        print(f"[AfterLoginUI] Channel created successfully: ID {channel_id}")

                    elif command[0] == "JOIN_SUCCESS":
                        print(f"[AfterLoginUI] {self.identifier} (ID: {self.user_id}) successfully joined channel {self.selected_channel_id}")
                        self.fetch_channels()

                    elif command[0] == "ALREADY_MEMBER":
                        print(f"[AfterLoginUI] {self.identifier} (ID: {self.user_id}) is already a member of channel {self.selected_channel_id}")

                    elif command[0] == "CHANNEL_NOT_FOUND":
                        print(f"[AfterLoginUI] Channel {self.selected_channel_id} not found for {self.identifier} (ID: {self.user_id})")

            except socket.timeout:
                # Timeout occurred, check if we should continue running
                continue
            except Exception as e:
                print(f"[AfterLoginUI] Error in listener for {self.identifier} (ID: {self.user_id}): {e}")
                break

    def create_channel_section(self, title, parent_frame, is_hosting=False):
        """Create a channel section with an optional 'Create a New Channel' button."""
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

        # Store the scrollable frame for dynamic updates
        if title == "Hosting channels":
            self.hosting_channels_frame = scrollable_frame
        elif title == "Joining channels":
            self.joining_channels_frame = scrollable_frame
        elif title == "Other channels":
            self.other_channels_frame = scrollable_frame

        # Customize scrollbar style to match dark theme
        style = ttk.Style()
        style.configure("Vertical.TScrollbar", background="#444444", troughcolor="#333333", borderwidth=0)

    def update_channel_lists(self):
        """Update the channel lists in all sections based on the current channels."""
        # Clear existing channel labels
        for frame in [self.hosting_channels_frame, self.joining_channels_frame, self.other_channels_frame]:
            for widget in frame.winfo_children():
                widget.destroy()

        # Populate Hosting channels (channels where the user is the host)
        for channel_id, channel in self.channels.items():
            if channel["host"] == self.user_id:
                channel_label = tk.Label(self.hosting_channels_frame, text=channel["name"], font=("Arial", 10), bg=self.sidebar_color, fg=self.text_color, cursor="hand2")
                channel_label.pack(anchor="w", padx=10, pady=2)
                channel_label.bind("<Button-1>", lambda e, cid=channel_id: self.select_channel(cid))

        # Populate Joining channels (channels where the user is a member but not the host)
        for channel_id, channel in self.channels.items():
            if self.user_id in channel["members"] and channel["host"] != self.user_id:
                channel_label = tk.Label(self.joining_channels_frame, text=channel["name"], font=("Arial", 10), bg=self.sidebar_color, fg=self.text_color, cursor="hand2")
                channel_label.pack(anchor="w", padx=10, pady=2)
                channel_label.bind("<Button-1>", lambda e, cid=channel_id: self.select_channel(cid))

        # Populate Other channels (channels where the user is neither a member nor the host)
        for channel_id, channel in self.channels.items():
            if self.user_id not in channel["members"] and channel["host"] != self.user_id:
                channel_label = tk.Label(self.other_channels_frame, text=channel["name"], font=("Arial", 10), bg=self.sidebar_color, fg=self.text_color, cursor="hand2")
                channel_label.pack(anchor="w", padx=10, pady=2)
                channel_label.bind("<Button-1>", lambda e, cid=channel_id: self.select_channel(cid))

    def select_channel(self, channel_id):
        """Handle channel selection by updating the main content area."""
        self.selected_channel_id = channel_id
        channel = self.channels[channel_id]

        # Clear the content frame
        for widget in self.content_frame.winfo_children():
            widget.destroy()

        # Display channel information
        channel_label = tk.Label(self.content_frame, text=f"Channel: {channel['name']}", font=("Arial", 16, "bold"), bg=self.main_color, fg=self.text_color)
        channel_label.pack(pady=20)

        # Check if the user is a member or the host
        if self.user_id in channel["members"] or channel["host"] == self.user_id:
            # User is a member or host, show a placeholder for chat (to be implemented later)
            tk.Label(self.content_frame, text="Chat area (to be implemented)", font=("Arial", 12), bg=self.main_color, fg=self.text_color).pack(pady=10)
        else:
            # User is not a member, show join option
            tk.Label(self.content_frame, text="You're not a member of this channel", font=("Arial", 12), bg=self.main_color, fg=self.text_color).pack(pady=10)
            join_btn = tk.Button(self.content_frame, text="Join this channel", command=lambda: self.join_channel(channel_id),
                                 bg=self.join_btn_color, fg="white", font=("Arial", 10))
            join_btn.pack(pady=5)

    def join_channel(self, channel_id):
        """Send a request to join the selected channel."""
        try:
            self.conn.sendall(f"JOIN_CHANNEL {self.user_id} {channel_id}".encode())
        except Exception as e:
            print(f"[AfterLoginUI] Error joining channel {channel_id} for {self.identifier} (ID: {self.user_id}): {e}")

    def on_create_channel(self):
        """Open a new window to create a channel."""
        print(f"[AfterLoginUI] 'Create a New Channel' button clicked by user: {self.identifier} (ID: {self.user_id})")

        # Create a new window for channel name input
        create_window = tk.Toplevel(self.root)
        create_window.title("Create a New Channel")
        create_window.geometry("300x150")
        create_window.configure(bg=self.main_color)

        tk.Label(create_window, text="Enter channel name:", bg=self.main_color, fg=self.text_color, font=("Arial", 12)).pack(pady=10)
        channel_name_entry = tk.Entry(create_window, width=25)
        channel_name_entry.pack(pady=5)

        def submit_channel():
            channel_name = channel_name_entry.get().strip()
            if channel_name:
                try:
                    self.conn.sendall(f"CREATE_CHANNEL {self.user_id} {channel_name}".encode())
                    create_window.destroy()
                except Exception as e:
                    print(f"[AfterLoginUI] Error creating channel for {self.identifier} (ID: {self.user_id}): {e}")
                    messagebox.showerror("Error", f"Failed to create channel: {e}")
            else:
                messagebox.showwarning("Warning", "Please enter a channel name.")

        tk.Button(create_window, text="OK", command=submit_channel, bg=self.create_btn_color, fg="white").pack(pady=10)

    def get_status_color(self):
        """Return the color for the status dot."""
        if self.mode == "visitor":
            return "gray"
        if self.status == "Online":
            return "green"
        elif self.status == "Invisible":
            return "black"
        else:
            return "red"

    def update_status(self, event=None):
        """Update the user's status and notify the server."""
        new_status = self.status_var.get()
        if new_status != self.status:
            print(f"[AfterLoginUI] User {self.identifier} (ID: {self.user_id}) attempting to change status from {self.status} to {new_status}")
            try:
                self.conn.sendall(f"SET_STATUS {self.user_id} {new_status}".encode())
                response = self.conn.recv(1024).decode()
                if response != "STATUS_UPDATED":
                    messagebox.showerror("Error", "Failed to update status on server.")
                    self.status_var.set(self.status)
                    print(f"[AfterLoginUI] Status update failed for {self.identifier} (ID: {self.user_id}): {response}")
                else:
                    self.status = new_status
                    self.status_label.config(text=f"Status: {self.status}")
                    self.dot_canvas.itemconfig(self.dot, fill=self.get_status_color())
                    print(f"[AfterLoginUI] Status updated successfully for {self.identifier} (ID: {self.user_id}): {self.status}")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to communicate with server: {e}")
                self.status_var.set(self.status)
                print(f"[AfterLoginUI] Status update error for {self.identifier} (ID: {self.user_id}): {e}")

    def close(self):
        """Close the UI and the socket connection."""
        print(f"[AfterLoginUI] Closing UI for user: {self.identifier} (ID: {self.user_id}), mode: {self.mode}")
        # Stop the listener thread
        self.running = False
        # Wait for the listener thread to finish
        try:
            self.listener_thread.join()
            print(f"[AfterLoginUI] Listener thread stopped for {self.identifier} (ID: {self.user_id})")
        except Exception as e:
            print(f"[AfterLoginUI] Error joining listener thread for {self.identifier} (ID: {self.user_id}): {e}")

        # Now that the listener thread is stopped, proceed with closing the socket
        if self.mode == "authenticated":
            try:
                self.conn.sendall(f"SET_STATUS {self.user_id} Offline".encode())
                # Temporarily disable timeout to ensure we get the response
                self.conn.settimeout(None)
                response = self.conn.recv(1024).decode()
                if response == "STATUS_UPDATED":
                    print(f"[AfterLoginUI] Set status to Offline for {self.identifier} (ID: {self.user_id})")
            except Exception as e:
                print(f"[AfterLoginUI] Error during logout status update for {self.identifier} (ID: {self.user_id}): {e}")
            finally:
                self.conn.close()
                print(f"[AfterLoginUI] Socket connection closed for {self.identifier} (ID: {self.user_id})")

        # Destroy the UI
        self.root.destroy()
        print(f"[AfterLoginUI] UI destroyed for {self.identifier} (ID: {self.user_id})")