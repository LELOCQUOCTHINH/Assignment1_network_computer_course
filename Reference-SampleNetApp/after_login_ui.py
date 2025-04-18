import tkinter as tk
from tkinter import messagebox, ttk
from tkinter import Canvas, Scrollbar
import threading
import socket
from datetime import datetime
import errno
import queue
import time

class AfterLoginUI:
    def __init__(self, mode, identifier, user_id, conn):
        self.mode = mode
        self.identifier = identifier
        self.user_id = user_id
        self.conn = conn
        # Initialize status as None; we'll fetch it for authenticated users
        self.status = "N/A" if mode == "visitor" else None

        # Set the socket to non-blocking mode
        self.conn.setblocking(False)

        self.channels = {}
        self.selected_channel_id = None
        self.user_id_to_username = {user_id: identifier}
        self.user_id_to_status = {user_id: self.status}  # Initialize with current user's status
        self.displayed_messages = set()
        self.joined_channels = set()
        self.response_queue = queue.Queue()
        # Add a queue for status update responses
        self.status_response_queue = queue.Queue()
        # Debounce mechanism for status updates
        self.last_status_change = 0
        self.status_debounce_delay = 0.5  # 500ms debounce delay

        print(f"[AfterLoginUI] Initializing UI for user: {self.identifier} (ID: {self.user_id}), mode: {self.mode}, initial status: {self.status}")

        self.bg_color = "#7289da"
        self.sidebar_color = "#2f3136"
        self.main_color = "#36393f"
        self.text_color = "#dcddde"
        self.logout_btn_color = "#FF4444"
        self.create_btn_color = "#7289da"
        self.join_btn_color = "#4CAF50"
        self.leave_btn_color = "#e74c3c"
        self.leave_btn_hover_color = "#ff5555"
        self.send_btn_color = "#7289da"

        self.root = tk.Tk()
        self.root.title(f"Chat App - {self.identifier}")
        self.root.geometry("800x600")
        self.root.configure(bg=self.bg_color)

        self.root.protocol("WM_DELETE_WINDOW", self.close)

        self.main_frame = tk.Frame(self.root, bg=self.bg_color)
        self.main_frame.pack(fill="both", expand=True)

        self.sidebar_frame = tk.Frame(self.main_frame, bg=self.sidebar_color, width=200)
        self.sidebar_frame.pack(side="left", fill="y")
        self.sidebar_frame.pack_propagate(False)

        self.hosting_frame = tk.Frame(self.sidebar_frame, bg=self.sidebar_color, height=166)
        self.hosting_frame.pack(fill="x")
        self.hosting_frame.pack_propagate(False)
        self.hosting_channels_frame = None
        self.create_channel_section("Hosting channels", self.hosting_frame, is_hosting=True)

        self.joining_frame = tk.Frame(self.sidebar_frame, bg=self.sidebar_color, height=166)
        self.joining_frame.pack(fill="x")
        self.joining_frame.pack_propagate(False)
        self.joining_channels_frame = None
        self.create_channel_section("Joining channels", self.joining_frame)

        self.other_frame = tk.Frame(self.sidebar_frame, bg=self.sidebar_color, height=166)
        self.other_frame.pack(fill="x")
        self.other_frame.pack_propagate(False)
        self.other_channels_frame = None
        self.create_channel_section("Other channels", self.other_frame)

        self.user_bar_section = tk.Frame(self.sidebar_frame, bg=self.sidebar_color, height=100)
        self.user_bar_section.pack(side="bottom", fill="x")
        self.user_bar_section.pack_propagate(False)

        self.user_bar_frame = tk.Frame(self.user_bar_section, bg=self.sidebar_color)
        self.user_bar_frame.pack(fill="x", padx=5, pady=5)

        self.user_label = tk.Label(self.user_bar_frame, text=self.identifier, font=("Arial", 10), bg=self.sidebar_color, fg=self.text_color)
        self.user_label.pack(anchor="w", pady=2)

        self.status_frame = tk.Frame(self.user_bar_frame, bg=self.sidebar_color)
        self.status_frame.pack(fill="x", pady=2)

        self.dot_canvas = tk.Canvas(self.status_frame, width=20, height=20, bg=self.sidebar_color, highlightthickness=0)
        self.dot = self.dot_canvas.create_oval(5, 5, 15, 15, fill=self.get_status_color())
        self.dot_canvas.pack(side="left")

        self.status_label = tk.Label(self.status_frame, text=f"Status: {self.status}", font=("Arial", 10), bg=self.sidebar_color, fg=self.text_color)
        self.status_label.pack(side="left", padx=5)

        if self.mode == "authenticated":
            # Fetch the user's status from the server
            self.status = self.fetch_own_status() or "Online"  # Fallback to "Online" if fetch fails
            self.user_id_to_status[self.user_id] = self.status
            print(f"[AfterLoginUI] Set initial status for {self.identifier} (ID: {self.user_id}) to {self.status}")
            self.status_var = tk.StringVar(value=self.status)
            self.status_dropdown = ttk.Combobox(self.status_frame, textvariable=self.status_var, values=["Online", "Invisible"], state="readonly", width=10)
            self.status_dropdown.pack(side="left", padx=5)
            self.status_dropdown.bind("<<ComboboxSelected>>", self.on_status_selected)
            # Update status label and dot after fetching
            self.status_label.config(text=f"Status: {self.status}")
            new_color = self.get_status_color(self.status)
            if new_color:
                self.dot_canvas.itemconfig(self.dot, fill=new_color, outline=new_color)
            else:
                self.dot_canvas.itemconfig(self.dot, fill="", outline="")

        self.logout_btn = tk.Button(self.user_bar_frame, text="LOGOUT", command=self.close, width=10, bg=self.logout_btn_color, fg="white", font=("Arial", 10))
        self.logout_btn.pack(anchor="w", pady=5)

        self.content_frame = tk.Frame(self.main_frame, bg=self.main_color)
        self.content_frame.pack(side="right", fill="both", expand=True)

        self.welcome_label = tk.Label(self.content_frame, text=f"WELCOME, {self.identifier}!\nYou are logged in as {self.mode}.", font=("Arial", 16, "bold"), bg=self.main_color, fg=self.text_color)
        self.welcome_label.pack(pady=50)

        self.chat_placeholder = tk.Label(self.content_frame, text="Chat features coming soon!", font=("Arial", 12), bg=self.main_color, fg=self.text_color)
        self.chat_placeholder.pack(pady=10)

        self.running = True
        self.listener_thread = threading.Thread(target=self.listen_for_updates)
        self.listener_thread.start()

        # Start a thread to process status update responses
        self.status_response_thread = threading.Thread(target=self.process_status_responses)
        self.status_response_thread.start()

        self.fetch_channels()

        self.root.mainloop()

    def fetch_own_status(self):
        """Fetch the user's own status from the server synchronously."""
        try:
            self.conn.sendall(f"GET_STATUS {self.user_id}".encode())
            print(f"[AfterLoginUI] Sent GET_STATUS request for own user_id {self.user_id}")
            # Wait briefly for the response
            start_time = time.time()
            timeout = 2.0  # 2-second timeout
            while time.time() - start_time < timeout:
                try:
                    response = self.conn.recv(1024).decode().strip()
                    if response:
                        print(f"[AfterLoginUI] Received status response for own user_id {self.user_id}: {response}")
                        command = response.split()
                        if command[0] == "STATUS" and command[1] == self.user_id:
                            return command[2]
                except socket.error as e:
                    if e.errno != errno.EWOULDBLOCK:
                        print(f"[AfterLoginUI] Socket error fetching own status for {self.identifier} (ID: {self.user_id}): {e}")
                        return None
                    time.sleep(0.01)  # Short sleep to prevent CPU hogging
            print(f"[AfterLoginUI] Timeout fetching own status for {self.identifier} (ID: {self.user_id})")
            return None
        except Exception as e:
            print(f"[AfterLoginUI] Error fetching own status for {self.identifier} (ID: {self.user_id}): {e}")
            return None

    def fetch_channels(self):
        try:
            self.conn.sendall("GET_CHANNELS".encode())
            print(f"[AfterLoginUI] Sent GET_CHANNELS request for {self.identifier} (ID: {self.user_id})")
        except Exception as e:
            print(f"[AfterLoginUI] Error fetching channels for {self.identifier} (ID: {self.user_id}): {e}")

    def fetch_messages(self, channel_id):
        try:
            self.conn.sendall(f"GET_MESSAGES {channel_id}".encode())
            print(f"[AfterLoginUI] Sent GET_MESSAGES request for channel {channel_id}")
        except Exception as e:
            print(f"[AfterLoginUI] Error fetching messages for channel {channel_id}: {e}")

    def fetch_username(self, user_id):
        if user_id in self.user_id_to_username:
            return self.user_id_to_username[user_id]
        try:
            self.conn.sendall(f"GET_USERNAME {user_id}".encode())
            while True:
                try:
                    response = self.conn.recv(1024).decode().strip()
                    if response:
                        break
                except socket.error as e:
                    if e.errno != errno.EWOULDBLOCK:
                        raise e
                    continue
            print(f"[AfterLoginUI] Received username response for user_id {user_id}: {response}")
            command = response.split()
            if command[0] == "USERNAME":
                _, fetched_user_id, username = command
                self.user_id_to_username[fetched_user_id] = username
                return username
            else:
                print(f"[AfterLoginUI] Username not found for user_id {user_id}")
                return user_id
        except Exception as e:
            print(f"[AfterLoginUI] Error fetching username for user_id {user_id}: {e}")
            return user_id

    def fetch_status(self, user_id):
        if user_id in self.user_id_to_status:
            return self.user_id_to_status[user_id]
        try:
            self.conn.sendall(f"GET_STATUS {user_id}".encode())
            print(f"[AfterLoginUI] Sent GET_STATUS request for user_id {user_id}")
            while True:
                try:
                    response = self.conn.recv(1024).decode().strip()
                    if response:
                        break
                except socket.error as e:
                    if e.errno != errno.EWOULDBLOCK:
                        raise e
                    continue
            print(f"[AfterLoginUI] Received status response for user_id {user_id}: {response}")
            command = response.split()
            if command[0] == "STATUS":
                _, fetched_user_id, status = command
                self.user_id_to_status[fetched_user_id] = status
                return status
            else:
                print(f"[AfterLoginUI] Status not found for user_id {user_id}, assuming Offline")
                self.user_id_to_status[user_id] = "Offline"
                return "Offline"
        except Exception as e:
            print(f"[AfterLoginUI] Error fetching status for user_id {user_id}: {e}")
            self.user_id_to_status[user_id] = "Offline"
            return "Offline"

    def get_status_color(self, status=None):
        if status is None:
            status = self.status
        if self.mode == "visitor":
            return "gray"
        if status == "Online":
            return "green"
        elif status == "Offline":
            return "black"
        elif status == "Invisible":
            return None  # No dot for Invisible
        else:
            return "black"  # Default to black for unknown statuses

    def listen_for_updates(self):
        while self.running:
            try:
                data = self.conn.recv(1024).decode()
                if not data:
                    print(f"[AfterLoginUI] Connection closed by server for {self.identifier} (ID: {self.user_id})")
                    break
                print(f"[AfterLoginUI] Received update for {self.identifier} (ID: {self.user_id}): {data}")
                messages = data.strip().split("\n")
                for message in messages:
                    if not message:
                        continue
                    command = message.split(maxsplit=3)

                    if command[0] == "NO_CHANNELS":
                        self.channels = {}
                        self.update_channel_lists()
                        print(f"[AfterLoginUI] No channels available, cleared channel list")

                    elif command[0] == "CHANNEL":
                        try:
                            parts = message.split()
                            channel_id = int(parts[1])
                            host = parts[2]
                            num_members = int(parts[3])
                            idx = 4
                            channel_name_parts = []
                            while idx < len(parts) and not parts[idx].isdigit():
                                channel_name_parts.append(parts[idx])
                                idx += 1
                            channel_name = " ".join(channel_name_parts)
                            num_visitors = int(parts[idx])
                            idx += 1
                            visitors = parts[idx:idx + num_visitors] if num_visitors > 0 else []
                            idx += num_visitors
                            num_regulars = int(parts[idx])
                            idx += 1
                            regular_members = parts[idx:idx + num_regulars] if num_regulars > 0 else []
                            self.channels[channel_id] = {
                                "name": channel_name,
                                "host": host,
                                "regular_members": regular_members,
                                "visitors": visitors
                            }
                            print(f"[AfterLoginUI] Parsed CHANNEL: channel_id={channel_id}, name={channel_name}, host={host}, regular_members={regular_members}, visitors={visitors}")
                            all_ids = regular_members + visitors + [host]
                            for member_id in all_ids:
                                if member_id not in self.user_id_to_username:
                                    self.fetch_username(member_id)
                                if member_id not in self.user_id_to_status:
                                    self.fetch_status(member_id)
                            self.update_channel_lists()
                            if self.selected_channel_id == channel_id:
                                print(f"[AfterLoginUI] Channel {channel_id} is currently selected, refreshing UI")
                                self.select_channel(channel_id)
                        except (ValueError, IndexError) as e:
                            print(f"[AfterLoginUI] Error parsing CHANNEL message: {message}, error: {e}")

                    elif command[0] == "UPDATE_CHANNELS":
                        try:
                            channel_id = int(command[1])
                            host = command[2]
                            channel_name = " ".join(command[3:])
                            print(f"[AfterLoginUI] Received UPDATE_CHANNELS for channel {channel_id}, fetching updated channel list")
                            self.fetch_channels()
                        except (ValueError, IndexError) as e:
                            print(f"[AfterLoginUI] Error parsing UPDATE_CHANNELS message: {message}, error: {e}")

                    elif command[0] == "CHANNEL_CREATED":
                        try:
                            channel_id = int(command[1])
                            print(f"[AfterLoginUI] Channel created successfully: ID {channel_id}")
                        except (ValueError, IndexError) as e:
                            print(f"[AfterLoginUI] Error parsing CHANNEL_CREATED message: {message}, error: {e}")

                    elif command[0] == "JOIN_SUCCESS":
                        print(f"[AfterLoginUI] {self.identifier} (ID: {self.user_id}) successfully joined channel {self.selected_channel_id}")
                        self.fetch_channels()

                    elif command[0] == "ALREADY_MEMBER":
                        print(f"[AfterLoginUI] {self.identifier} (ID: {self.user_id}) is already a member of channel {self.selected_channel_id}")

                    elif command[0] == "CHANNEL_NOT_FOUND":
                        print(f"[AfterLoginUI] Channel {self.selected_channel_id} not found for {self.identifier} (ID: {self.user_id})")

                    elif command[0] == "MESSAGE":
                        try:
                            channel_id = command[1]
                            user_id = command[2]
                            rest = message.split(maxsplit=3)[3]
                            timestamp, msg = rest.split(" | ", 1)
                            if channel_id == str(self.selected_channel_id):
                                username = self.get_username(user_id)
                                self.display_message(username, timestamp, msg)
                        except (IndexError, ValueError) as e:
                            print(f"[AfterLoginUI] Error parsing MESSAGE: {message}, error: {e}")

                    elif command[0] == "NO_MESSAGES":
                        pass

                    elif command[0] == "MESSAGE_SENT":
                        print(f"[AfterLoginUI] Message sent successfully for {self.identifier} (ID: {self.user_id})")
                        self.root.after(0, self.message_entry.delete, 0, tk.END)

                    elif command[0] in ["VISITOR_NOT_ALLOWED", "CHANNEL_NOT_FOUND", "NOT_A_MEMBER"]:
                        error_msg = {
                            "VISITOR_NOT_ALLOWED": "Visitors cannot send messages.",
                            "CHANNEL_NOT_FOUND": "The channel no longer exists.",
                            "NOT_A_MEMBER": "You are not a member of this channel."
                        }.get(command[0], f"Failed to send message: {message}")
                        print(f"[AfterLoginUI] Error sending message for {self.identifier} (ID: {self.user_id}): {error_msg}")
                        self.root.after(0, messagebox.showerror, "Error", error_msg)

                    elif command[0] == "LEAVE_SUCCESS":
                        self.response_queue.put(("LEAVE_SUCCESS", message))
                        print(f"[AfterLoginUI] Queued LEAVE_SUCCESS response for {self.identifier} (ID: {self.user_id})")

                    elif command[0] in ["CHANNEL_NOT_FOUND", "NOT_A_MEMBER"]:
                        self.response_queue.put(("ERROR", message))
                        print(f"[AfterLoginUI] Queued error response for LEAVE_CHANNEL: {message}")

                    elif command[0] == "STATUS":
                        try:
                            _, user_id, status = command
                            self.user_id_to_status[user_id] = status
                            print(f"[AfterLoginUI] Updated status for user_id {user_id}: {status}")
                            if self.selected_channel_id:
                                channel = self.channels.get(self.selected_channel_id)
                                if channel:
                                    all_members = [channel["host"]] + channel["regular_members"] + channel["visitors"]
                                    if user_id in all_members:
                                        self.select_channel(self.selected_channel_id)
                        except (ValueError, IndexError) as e:
                            print(f"[AfterLoginUI] Error parsing STATUS message: {message}, error: {e}")

                    elif command[0] == "STATUS_UPDATED" or command[0] == "INVALID_STATUS" or command[0] == "USER_NOT_FOUND":
                        # Queue the status update response to be processed by the status response thread
                        self.status_response_queue.put((command[0], message))
                        print(f"[AfterLoginUI] Queued status response: {message}")

            except socket.error as e:
                if e.errno == errno.EWOULDBLOCK:
                    continue
                else:
                    print(f"[AfterLoginUI] Socket error in listener for {self.identifier} (ID: {self.user_id}): {e}")
                    break
            except Exception as e:
                print(f"[AfterLoginUI] Error in listener for {self.identifier} (ID: {self.user_id}): {e}")
                break

        print(f"[AfterLoginUI] Listener thread exiting for {self.identifier} (ID: {self.user_id})")

    def process_status_responses(self):
        """Process status update responses asynchronously."""
        while self.running:
            try:
                response_type, response = self.status_response_queue.get(timeout=1)
                self.root.after(0, self.handle_status_response, response_type, response)
            except queue.Empty:
                continue
            except Exception as e:
                print(f"[AfterLoginUI] Error processing status response for {self.identifier} (ID: {self.user_id}): {e}")

    def handle_status_response(self, response_type, response):
        """Handle the status update response in the main GUI thread."""
        if response_type == "STATUS_UPDATED":
            new_status = self.status_var.get()
            self.status = new_status
            self.user_id_to_status[self.user_id] = new_status
            self.status_label.config(text=f"Status: {self.status}")
            # Update the dot's color
            new_color = self.get_status_color(new_status)
            if new_color:
                self.dot_canvas.itemconfig(self.dot, fill=new_color)
                self.dot_canvas.itemconfig(self.dot, outline=new_color)
            else:
                # For Invisible, hide the dot by setting fill and outline to transparent
                self.dot_canvas.itemconfig(self.dot, fill="", outline="")
            print(f"[AfterLoginUI] Status updated successfully for {self.identifier} (ID: {self.user_id}): {self.status}, dot color: {new_color}")
        else:
            messagebox.showerror("Error", "Failed to update status on server.")
            self.status_var.set(self.status)
            print(f"[AfterLoginUI] Status update failed for {self.identifier} (ID: {self.user_id}): {response}")

    def get_username(self, user_id):
        if user_id in self.user_id_to_username:
            return self.user_id_to_username[user_id]
        return self.fetch_username(user_id)

    def create_channel_section(self, title, parent_frame, is_hosting=False):
        print(f"[AfterLoginUI] Creating channel section: {title}, is_hosting: {is_hosting}")

        section_frame = tk.Frame(parent_frame, bg=self.sidebar_color)
        section_frame.pack(fill="both", expand=True, padx=5, pady=5)

        if is_hosting and self.mode == "authenticated":
            create_btn = tk.Button(section_frame, text="Create a New Channel", command=self.on_create_channel,
                                   bg=self.create_btn_color, fg="white", font=("Arial", 10))
            create_btn.pack(anchor="w", padx=5, pady=2)
            print(f"[AfterLoginUI] Added 'Create a New Channel' button to {title} section for authenticated user")

        title_label = tk.Label(section_frame, text=title, font=("Arial", 12, "bold"), bg=self.sidebar_color, fg=self.text_color)
        title_label.pack(anchor="w", padx=5)

        canvas = Canvas(section_frame, bg=self.sidebar_color, highlightthickness=0)
        scrollbar = ttk.Scrollbar(section_frame, orient="vertical", command=canvas.yview, style="Vertical.TScrollbar")
        scrollable_frame = tk.Frame(canvas, bg=self.sidebar_color)

        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )

        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        scrollbar.pack(side="left", fill="y")
        canvas.pack(side="left", fill="both", expand=True)

        if title == "Hosting channels":
            self.hosting_channels_frame = scrollable_frame
        elif title == "Joining channels":
            self.joining_channels_frame = scrollable_frame
        elif title == "Other channels":
            self.other_channels_frame = scrollable_frame

        style = ttk.Style()
        style.configure("Vertical.TScrollbar", background="#444444", troughcolor="#333333", borderwidth=0)

    def update_channel_lists(self):
        for frame in [self.hosting_channels_frame, self.joining_channels_frame, self.other_channels_frame]:
            for widget in frame.winfo_children():
                widget.destroy()

        print(f"[AfterLoginUI] Updating channel lists for user_id={self.user_id}, type={type(self.user_id)}, channels={self.channels}")

        for channel_id, channel in self.channels.items():
            is_host = channel["host"] == self.user_id
            print(f"[AfterLoginUI] Checking channel {channel_id} for Hosting: host={channel['host']}, type={type(channel['host'])}, user_id={self.user_id}, type={type(self.user_id)}, match={is_host}")
            if is_host:
                label_text = channel["name"]
                channel_label = tk.Label(self.hosting_channels_frame, text=label_text, font=("Arial", 10), bg=self.sidebar_color, fg=self.text_color, cursor="hand2")
                channel_label.pack(anchor="w", padx=10, pady=2)
                channel_label.bind("<Button-1>", lambda e, cid=channel_id: self.select_channel(cid))
                print(f"[AfterLoginUI] Added channel to Hosting channels: ID={channel_id}, display_text={label_text}, actual_text={channel_label.cget('text')}")

        for channel_id, channel in self.channels.items():
            all_members = channel["regular_members"] + channel["visitors"]
            is_member = self.user_id in all_members
            is_host = channel["host"] == self.user_id
            print(f"[AfterLoginUI] Checking channel {channel_id} for Joining: members={all_members}, user_id={self.user_id}, is_member={is_member}, is_host={is_host}")
            if is_member and not is_host:
                label_text = channel["name"]
                channel_label = tk.Label(self.joining_channels_frame, text=label_text, font=("Arial", 10), bg=self.sidebar_color, fg=self.text_color, cursor="hand2")
                channel_label.pack(anchor="w", padx=10, pady=2)
                channel_label.bind("<Button-1>", lambda e, cid=channel_id: self.select_channel(cid))
                print(f"[AfterLoginUI] Added channel to Joining channels: ID={channel_id}, display_text={label_text}, actual_text={channel_label.cget('text')}")

        for channel_id, channel in self.channels.items():
            all_members = channel["regular_members"] + channel["visitors"]
            is_member = self.user_id in all_members
            is_host = channel["host"] == self.user_id
            print(f"[AfterLoginUI] Checking channel {channel_id} for Other: members={all_members}, user_id={self.user_id}, is_member={is_member}, is_host={is_host}")
            if not is_member and not is_host:
                label_text = channel["name"]
                channel_label = tk.Label(self.other_channels_frame, text=label_text, font=("Arial", 10), bg=self.sidebar_color, fg=self.text_color, cursor="hand2")
                channel_label.pack(anchor="w", padx=10, pady=2)
                channel_label.bind("<Button-1>", lambda e, cid=channel_id: self.select_channel(cid))
                print(f"[AfterLoginUI] Added channel to Other channels: ID={channel_id}, display_text={label_text}, actual_text={channel_label.cget('text')}")

        self.root.update()

    def select_channel(self, channel_id):
        self.selected_channel_id = channel_id
        channel = self.channels.get(channel_id)
        if not channel:
            print(f"[AfterLoginUI] Channel {channel_id} not found in self.channels")
            return

        self.displayed_messages.clear()
        print(f"[AfterLoginUI] Cleared displayed messages for channel {channel_id}")

        for widget in self.content_frame.winfo_children():
            widget.destroy()

        chat_main_frame = tk.Frame(self.content_frame, bg=self.main_color)
        chat_main_frame.pack(fill="both", expand=True)

        chat_left_frame = tk.Frame(chat_main_frame, bg=self.main_color)
        chat_left_frame.pack(side="left", fill="both", expand=True)

        channel_label = tk.Label(chat_left_frame, text=f"{channel['name']}", font=("Arial", 16, "bold"), bg=self.main_color, fg=self.text_color)
        channel_label.pack(pady=10)

        message_frame = tk.Frame(chat_left_frame, bg=self.main_color)
        message_frame.pack(fill="both", expand=True, padx=10)

        canvas = Canvas(message_frame, bg=self.main_color, highlightthickness=0)
        scrollbar = ttk.Scrollbar(message_frame, orient="vertical", command=canvas.yview)
        self.message_scrollable_frame = tk.Frame(canvas, bg=self.main_color)

        self.message_scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )

        canvas.create_window((0, 0), window=self.message_scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        scrollbar.pack(side="right", fill="y")
        canvas.pack(side="left", fill="both", expand=True)

        input_frame = tk.Frame(chat_left_frame, bg=self.main_color)
        input_frame.pack(fill="x", padx=10, pady=5)

        self.message_entry = tk.Entry(input_frame, bg="#2f3136", fg=self.text_color, font=("Arial", 10))
        self.message_entry.pack(side="left", fill="x", expand=True, padx=(0, 5))

        send_btn = tk.Button(input_frame, text="Send", command=self.send_message, bg=self.send_btn_color, fg="white", font=("Arial", 10))
        send_btn.pack(side="left")

        if self.mode == "visitor":
            self.message_entry.config(state="disabled")
            send_btn.config(state="disabled")

        member_frame = tk.Frame(chat_main_frame, bg=self.main_color, width=150)
        member_frame.pack(side="right", fill="y")
        member_frame.pack_propagate(False)

        tk.Label(member_frame, text="Members", font=("Arial", 12, "bold"), bg=self.main_color, fg=self.text_color).pack(pady=5)

        host_username = self.get_username(channel["host"])
        host_status = self.fetch_status(channel["host"])
        host_frame = tk.Frame(member_frame, bg=self.main_color)
        host_frame.pack(anchor="w", padx=10, pady=2)
        tk.Label(host_frame, text=f"The host: {host_username}", font=("Arial", 10), bg=self.main_color, fg=self.text_color).pack(side="left")
        host_status_color = self.get_status_color(host_status)
        if host_status_color:
            host_dot_canvas = tk.Canvas(host_frame, width=14, height=14, bg=self.main_color, highlightthickness=0)
            host_dot_canvas.create_oval(4, 4, 10, 10, fill=host_status_color)
            host_dot_canvas.pack(side="left", padx=(5, 0))

        other_members = [(member, self.get_username(member)) for member in channel["regular_members"] if member != channel["host"]]
        if other_members:
            tk.Label(member_frame, text="Other members:", font=("Arial", 10), bg=self.main_color, fg=self.text_color).pack(anchor="w", padx=10, pady=2)
            for member_id, member_name in other_members:
                member_frame_inner = tk.Frame(member_frame, bg=self.main_color)
                member_frame_inner.pack(anchor="w", padx=20, pady=1)
                tk.Label(member_frame_inner, text=member_name, font=("Arial", 10), bg=self.main_color, fg=self.text_color).pack(side="left")
                member_status = self.fetch_status(member_id)
                member_status_color = self.get_status_color(member_status)
                if member_status_color:
                    member_dot_canvas = tk.Canvas(member_frame_inner, width=14, height=14, bg=self.main_color, highlightthickness=0)
                    member_dot_canvas.create_oval(4, 4, 10, 10, fill=member_status_color)
                    member_dot_canvas.pack(side="left", padx=(5, 0))

        visitors = [(visitor, self.get_username(visitor)) for visitor in channel["visitors"]]
        if visitors:
            tk.Label(member_frame, text="Visitors:", font=("Arial", 10), bg=self.main_color, fg=self.text_color).pack(anchor="w", padx=10, pady=2)
            for visitor_id, visitor_name in visitors:
                visitor_frame = tk.Frame(member_frame, bg=self.main_color)
                visitor_frame.pack(anchor="w", padx=20, pady=1)
                tk.Label(visitor_frame, text=visitor_name, font=("Arial", 10), bg=self.main_color, fg=self.text_color).pack(side="left")
                visitor_status = self.fetch_status(visitor_id)
                visitor_status_color = self.get_status_color(visitor_status)
                if visitor_status_color:
                    visitor_dot_canvas = tk.Canvas(visitor_frame, width=14, height=14, bg=self.main_color, highlightthickness=0)
                    visitor_dot_canvas.create_oval(4, 4, 10, 10, fill=visitor_status_color)
                    visitor_dot_canvas.pack(side="left", padx=(5, 0))

        all_members = channel["regular_members"] + channel["visitors"]
        is_host = channel["host"] == self.user_id
        if self.user_id in all_members and not is_host:
            leave_btn = tk.Button(
                member_frame,
                text="LEAVE CHANNEL",
                command=lambda: self.leave_channel(channel_id),
                width=15,
                bg=self.leave_btn_color,
                fg=self.text_color,
                font=("Arial", 10),
                borderwidth=1,
                highlightthickness=1,
                highlightbackground=self.sidebar_color,
                relief="raised",
                padx=10,
                pady=5
            )
            leave_btn.pack(pady=10)

            leave_btn.bind("<Enter>", lambda e: leave_btn.config(bg=self.leave_btn_hover_color))
            leave_btn.bind("<Leave>", lambda e: leave_btn.config(bg=self.leave_btn_color))
        else:
            if not is_host:
                tk.Label(chat_left_frame, text="You're not a member of this channel", font=("Arial", 12), bg=self.main_color, fg=self.text_color).pack(pady=10)
                join_btn = tk.Button(chat_left_frame, text="Join this channel", command=lambda: self.join_channel(channel_id),
                                     bg=self.join_btn_color, fg="white", font=("Arial", 10))
                join_btn.pack(pady=5)

        if self.user_id in all_members:
            self.fetch_messages(channel_id)

    def display_message(self, username, timestamp, message):
        message_id = f"{self.selected_channel_id}:{username}:{timestamp}:{message}"
        if message_id in self.displayed_messages:
            print(f"[AfterLoginUI] Skipped duplicate message: {message_id}")
            return
        self.displayed_messages.add(message_id)
        msg_text = f"{username} ({timestamp}): {message}"
        msg_label = tk.Label(self.message_scrollable_frame, text=msg_text, font=("Arial", 10), bg=self.main_color, fg=self.text_color, anchor="w", wraplength=400, justify="left")
        msg_label.pack(fill="x", padx=5, pady=2)
        print(f"[AfterLoginUI] Displayed message: {msg_text}")

    def send_message(self):
        message = self.message_entry.get().strip()
        if message and self.selected_channel_id:
            try:
                self.conn.sendall(f"SEND_MESSAGE {self.user_id} {self.selected_channel_id} {message}".encode())
                print(f"[AfterLoginUI] Sent SEND_MESSAGE request for {self.identifier} (ID: {self.user_id}): {message}")
            except Exception as e:
                print(f"[AfterLoginUI] Error sending message for {self.identifier} (ID: {self.user_id}): {e}")
                messagebox.showerror("Error", f"Failed to send message: {e}")

    def join_channel(self, channel_id):
        try:
            self.conn.sendall(f"JOIN_CHANNEL {self.user_id} {channel_id}".encode())
            print(f"[AfterLoginUI] Sent JOIN_CHANNEL request for channel {channel_id}")
            self.joined_channels.add(channel_id)
            print(f"[AfterLoginUI] Added channel {channel_id} to joined channels for {self.identifier} (ID: {self.user_id})")
        except Exception as e:
            print(f"[AfterLoginUI] Error joining channel {channel_id} for {self.identifier} (ID: {self.user_id}): {e}")

    def leave_channel(self, channel_id):
        channel = self.channels.get(channel_id)
        if not channel:
            print(f"[AfterLoginUI] Channel {channel_id} not found in self.channels")
            messagebox.showerror("Error", "Channel not found.")
            return

        if channel["host"] == self.user_id:
            error_msg = "You are the host of this channel and cannot leave."
            print(f"[AfterLoginUI] Error leaving channel {channel_id}: {error_msg}")
            messagebox.showerror("Error", error_msg)
            return

        try:
            while not self.response_queue.empty():
                self.response_queue.get_nowait()

            self.conn.sendall(f"LEAVE_CHANNEL {self.user_id} {channel_id}".encode())
            print(f"[AfterLoginUI] Sent LEAVE_CHANNEL request for channel {channel_id}")

            response_type, response = self.response_queue.get(timeout=5)
            print(f"[AfterLoginUI] Received response for LEAVE_CHANNEL: {response}")

            if response_type == "LEAVE_SUCCESS":
                messagebox.showinfo("Info", f"You have left channel {self.channels[channel_id]['name']}.")
                self.joined_channels.discard(channel_id)
                print(f"[AfterLoginUI] Removed channel {channel_id} from joined channels for {self.identifier} (ID: {self.user_id})")
            else:
                error_msg = {
                    "CHANNEL_NOT_FOUND": "The channel no longer exists.",
                    "NOT_A_MEMBER": "You are not a member of this channel."
                }.get(response.split()[0], f"Failed to leave channel: {response}")
                messagebox.showerror("Error", error_msg)
                print(f"[AfterLoginUI] Error leaving channel {channel_id}: {error_msg}")
                return

        except queue.Empty:
            print(f"[AfterLoginUI] Timeout waiting for LEAVE_CHANNEL response for channel {channel_id}")
            self.fetch_channels()
            channel = self.channels.get(channel_id)
            if channel and self.user_id not in (channel["regular_members"] + channel["visitors"]):
                messagebox.showinfo("Info", f"You have left channel {self.channels[channel_id]['name']}.")
                self.joined_channels.discard(channel_id)
                print(f"[AfterLoginUI] Removed channel {channel_id} from joined channels for {self.identifier} (ID: {self.user_id})")
            else:
                messagebox.showerror("Error", "Failed to leave channel: No response from server.")
                return
        except Exception as e:
            print(f"[AfterLoginUI] Error leaving channel {channel_id} for {self.identifier} (ID: {self.user_id}): {e}")
            messagebox.showerror("Error", f"Failed to leave channel: {e}")
            return

        self.selected_channel_id = None
        self.displayed_messages.clear()
        print(f"[AfterLoginUI] Cleared displayed messages after leaving channel {channel_id}")
        for widget in self.content_frame.winfo_children():
            widget.destroy()
        self.welcome_label = tk.Label(self.content_frame, text=f"WELCOME, {self.identifier}!\nYou are logged in as {self.mode}.", font=("Arial", 16, "bold"), bg=self.main_color, fg=self.text_color)
        self.welcome_label.pack(pady=50)
        self.chat_placeholder = tk.Label(self.content_frame, text="Chat features coming soon!", font=("Arial", 12), bg=self.main_color, fg=self.text_color)
        self.chat_placeholder.pack(pady=10)
        self.fetch_channels()

    def on_create_channel(self):
        print(f"[AfterLoginUI] 'Create a New Channel' button clicked by user: {self.identifier} (ID: {self.user_id})")

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

    def on_status_selected(self, event=None):
        """Handle status selection with debouncing."""
        new_status = self.status_var.get()
        current_time = time.time()
        if new_status != self.status:
            # Debounce: Ignore status changes that occur too quickly
            if current_time - self.last_status_change < self.status_debounce_delay:
                print(f"[AfterLoginUI] Debounced status change for {self.identifier} (ID: {self.user_id}): {new_status}")
                self.status_var.set(self.status)  # Revert to current status
                return
            self.last_status_change = current_time
            print(f"[AfterLoginUI] User {self.identifier} (ID: {self.user_id}) attempting to change status from {self.status} to {new_status}")
            try:
                self.conn.sendall(f"SET_STATUS {self.user_id} {new_status}".encode())
                print(f"[AfterLoginUI] Sent SET_STATUS {new_status} for {self.identifier} (ID: {self.user_id})")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to communicate with server: {e}")
                self.status_var.set(self.status)
                print(f"[AfterLoginUI] Status update error for {self.identifier} (ID: {self.user_id}): {e}")

    def close(self):
        print(f"[AfterLoginUI] Closing UI for user: {self.identifier} (ID: {self.user_id}), mode: {self.mode}")
        self.running = False

        if self.mode == "visitor":
            for channel_id in list(self.joined_channels):
                try:
                    self.conn.sendall(f"LEAVE_CHANNEL {self.user_id} {channel_id}".encode())
                    print(f"[AfterLoginUI] Sent LEAVE_CHANNEL request for channel {channel_id} during logout")
                    while True:
                        try:
                            response = self.conn.recv(1024).decode().strip()
                            if response:
                                break
                        except socket.error as e:
                            if e.errno != errno.EWOULDBLOCK:
                                raise e
                            continue
                    print(f"[AfterLoginUI] Received response for LEAVE_CHANNEL during logout: {response}")
                    if response == "LEAVE_SUCCESS":
                        self.joined_channels.discard(channel_id)
                        print(f"[AfterLoginUI] Successfully left channel {channel_id} during logout for {self.identifier} (ID: {self.user_id})")
                    else:
                        print(f"[AfterLoginUI] Failed to leave channel {channel_id} during logout: {response}")
                except Exception as e:
                    print(f"[AfterLoginUI] Error leaving channel {channel_id} during logout for {self.identifier} (ID: {self.user_id}): {e}")

        if self.mode == "authenticated" and self.status != "Invisible":
            try:
                self.conn.sendall(f"SET_STATUS {self.user_id} Offline".encode())
                print(f"[AfterLoginUI] Sent SET_STATUS Offline for {self.identifier} (ID: {self.user_id})")
                while True:
                    try:
                        response = self.conn.recv(1024).decode().strip()
                        if response:
                            break
                    except socket.error as e:
                        if e.errno != errno.EWOULDBLOCK:
                            raise e
                        continue
                if response == "STATUS_UPDATED":
                    print(f"[AfterLoginUI] Set status to Offline for {self.identifier} (ID: {self.user_id})")
                else:
                    print(f"[AfterLoginUI] Failed to set status to Offline for {self.identifier} (ID: {self.user_id}): {response}")
            except Exception as e:
                print(f"[AfterLoginUI] Error during logout status update for {self.identifier} (ID: {self.user_id}): {e}")

        try:
            self.conn.shutdown(socket.SHUT_RDWR)
            print(f"[AfterLoginUI] Socket shutdown for {self.identifier} (ID: {self.user_id})")
        except Exception as e:
            print(f"[AfterLoginUI] Error shutting down socket for {self.identifier} (ID: {self.user_id}): {e}")

        try:
            self.listener_thread.join()
            self.status_response_thread.join()
            print(f"[AfterLoginUI] Threads stopped for {self.identifier} (ID: {self.user_id})")
        except Exception as e:
            print(f"[AfterLoginUI] Error joining threads for {self.identifier} (ID: {self.user_id}): {e}")

        try:
            self.conn.close()
            print(f"[AfterLoginUI] Socket connection closed for {self.identifier} (ID: {self.user_id})")
        except Exception as e:
            print(f"[AfterLoginUI] Error closing socket for {self.identifier} (ID: {self.user_id}): {e}")

        self.root.destroy()
        print(f"[AfterLoginUI] UI destroyed for {self.identifier} (ID: {self.user_id})")