import tkinter as tk
from tkinter import messagebox, ttk
from tkinter import Canvas, Scrollbar
import threading
import socket
from datetime import datetime
import errno

class AfterLoginUI:
    def __init__(self, mode, identifier, user_id, conn):
        self.mode = mode
        self.identifier = identifier
        self.user_id = user_id
        self.conn = conn
        self.status = "Online" if mode == "authenticated" else "N/A"

        # Set the socket to non-blocking mode
        self.conn.setblocking(False)

        self.channels = {}
        self.selected_channel_id = None
        self.user_id_to_username = {user_id: identifier}
        # Set to keep track of displayed messages to avoid duplicates
        self.displayed_messages = set()
        # Set to keep track of channels the user has joined
        self.joined_channels = set()

        print(f"[AfterLoginUI] Initializing UI for user: {self.identifier} (ID: {self.user_id}), mode: {self.mode}, initial status: {self.status}")

        self.bg_color = "#7289da"
        self.sidebar_color = "#2f3136"
        self.main_color = "#36393f"
        self.text_color = "#dcddde"
        self.logout_btn_color = "#FF4444"
        self.create_btn_color = "#7289da"
        self.join_btn_color = "#4CAF50"
        self.leave_btn_color = "#FF4444"
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
            self.status_var = tk.StringVar(value=self.status)
            self.status_dropdown = ttk.Combobox(self.status_frame, textvariable=self.status_var, values=["Online", "Invisible"], state="readonly", width=10)
            self.status_dropdown.pack(side="left", padx=5)
            self.status_dropdown.bind("<<ComboboxSelected>>", self.update_status)

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

        self.fetch_channels()

        self.root.mainloop()

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
            # Since the socket is non-blocking, loop until we get the response
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

    def listen_for_updates(self):
        while self.running:
            try:
                # Non-blocking recv
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
                        # Handle the response to SEND_MESSAGE
                        print(f"[AfterLoginUI] Message sent successfully for {self.identifier} (ID: {self.user_id})")
                        # Use root.after to schedule the UI update on the main thread
                        self.root.after(0, self.message_entry.delete, 0, tk.END)

                    elif command[0] in ["VISITOR_NOT_ALLOWED", "CHANNEL_NOT_FOUND", "NOT_A_MEMBER"]:
                        # Handle error responses for SEND_MESSAGE
                        error_msg = {
                            "VISITOR_NOT_ALLOWED": "Visitors cannot send messages.",
                            "CHANNEL_NOT_FOUND": "The channel no longer exists.",
                            "NOT_A_MEMBER": "You are not a member of this channel."
                        }.get(command[0], f"Failed to send message: {message}")
                        print(f"[AfterLoginUI] Error sending message for {self.identifier} (ID: {self.user_id}): {error_msg}")
                        # Use root.after to schedule the error message on the main thread
                        self.root.after(0, messagebox.showerror, "Error", error_msg)

            except socket.error as e:
                if e.errno == errno.EWOULDBLOCK:
                    # No data available, continue the loop to check self.running
                    continue
                else:
                    print(f"[AfterLoginUI] Socket error in listener for {self.identifier} (ID: {self.user_id}): {e}")
                    break
            except Exception as e:
                print(f"[AfterLoginUI] Error in listener for {self.identifier} (ID: {self.user_id}): {e}")
                break

        print(f"[AfterLoginUI] Listener thread exiting for {self.identifier} (ID: {self.user_id})")

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

        # Clear displayed messages when switching channels to avoid filtering across channels
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
        tk.Label(member_frame, text=f"The host: {host_username}", font=("Arial", 10), bg=self.main_color, fg=self.text_color).pack(anchor="w", padx=10, pady=2)

        other_members = [self.get_username(member) for member in channel["regular_members"] if member != channel["host"]]
        if other_members:
            tk.Label(member_frame, text="Other members:", font=("Arial", 10), bg=self.main_color, fg=self.text_color).pack(anchor="w", padx=10, pady=2)
            for member in other_members:
                tk.Label(member_frame, text=member, font=("Arial", 10), bg=self.main_color, fg=self.text_color).pack(anchor="w", padx=20, pady=1)

        visitors = [self.get_username(visitor) for visitor in channel["visitors"]]
        if visitors:
            tk.Label(member_frame, text="Visitors:", font=("Arial", 10), bg=self.main_color, fg=self.text_color).pack(anchor="w", padx=10, pady=2)
            for visitor in visitors:
                tk.Label(member_frame, text=visitor, font=("Arial", 10), bg=self.main_color, fg=self.text_color).pack(anchor="w", padx=20, pady=1)

        all_members = channel["regular_members"] + channel["visitors"]
        if self.user_id in all_members:
            leave_btn = tk.Button(chat_main_frame, text="Leave Channel", command=lambda: self.leave_channel(channel_id),
                                  bg=self.leave_btn_color, fg="white", font=("Arial", 10))
            leave_btn.pack(side="bottom", anchor="se", padx=10, pady=5)
        else:
            tk.Label(chat_left_frame, text="You're not a member of this channel", font=("Arial", 12), bg=self.main_color, fg=self.text_color).pack(pady=10)
            join_btn = tk.Button(chat_left_frame, text="Join this channel", command=lambda: self.join_channel(channel_id),
                                 bg=self.join_btn_color, fg="white", font=("Arial", 10))
            join_btn.pack(pady=5)

        if self.user_id in all_members:
            self.fetch_messages(channel_id)

    def display_message(self, username, timestamp, message):
        # Create a unique identifier for the message
        message_id = f"{self.selected_channel_id}:{username}:{timestamp}:{message}"
        # Check if the message has already been displayed
        if message_id in self.displayed_messages:
            print(f"[AfterLoginUI] Skipped duplicate message: {message_id}")
            return
        # Add the message to the set of displayed messages
        self.displayed_messages.add(message_id)
        # Display the message
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
                # Response will be handled by listen_for_updates
            except Exception as e:
                print(f"[AfterLoginUI] Error sending message for {self.identifier} (ID: {self.user_id}): {e}")
                messagebox.showerror("Error", f"Failed to send message: {e}")

    def join_channel(self, channel_id):
        try:
            self.conn.sendall(f"JOIN_CHANNEL {self.user_id} {channel_id}".encode())
            print(f"[AfterLoginUI] Sent JOIN_CHANNEL request for channel {channel_id}")
            # Add the channel to the set of joined channels
            self.joined_channels.add(channel_id)
            print(f"[AfterLoginUI] Added channel {channel_id} to joined channels for {self.identifier} (ID: {self.user_id})")
        except Exception as e:
            print(f"[AfterLoginUI] Error joining channel {channel_id} for {self.identifier} (ID: {self.user_id}): {e}")

    def leave_channel(self, channel_id):
        try:
            self.conn.sendall(f"LEAVE_CHANNEL {self.user_id} {channel_id}".encode())
            print(f"[AfterLoginUI] Sent LEAVE_CHANNEL request for channel {channel_id}")
            # Wait for the response since the socket is non-blocking
            while True:
                try:
                    response = self.conn.recv(1024).decode().strip()
                    if response:
                        break
                except socket.error as e:
                    if e.errno != errno.EWOULDBLOCK:
                        raise e
                    continue
            print(f"[AfterLoginUI] Received response for LEAVE_CHANNEL: {response}")
            if response == "LEAVE_SUCCESS":
                messagebox.showinfo("Info", f"You have left channel {self.channels[channel_id]['name']}.")
                # Remove the channel from the set of joined channels
                self.joined_channels.discard(channel_id)
                print(f"[AfterLoginUI] Removed channel {channel_id} from joined channels for {self.identifier} (ID: {self.user_id})")
            else:
                messagebox.showerror("Error", f"Failed to leave channel: {response}")
        except Exception as e:
            print(f"[AfterLoginUI] Error leaving channel {channel_id} for {self.identifier} (ID: {self.user_id}): {e}")
            messagebox.showerror("Error", f"Failed to leave channel: {e}")

        self.selected_channel_id = None
        # Clear displayed messages when leaving a channel
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

    def get_status_color(self):
        if self.mode == "visitor":
            return "gray"
        if self.status == "Online":
            return "green"
        elif self.status == "Invisible":
            return "black"
        else:
            return "red"

    def update_status(self, event=None):
        new_status = self.status_var.get()
        if new_status != self.status:
            print(f"[AfterLoginUI] User {self.identifier} (ID: {self.user_id}) attempting to change status from {self.status} to {new_status}")
            try:
                self.conn.sendall(f"SET_STATUS {self.user_id} {new_status}".encode())
                # Since the socket is non-blocking, loop until we get the response
                while True:
                    try:
                        response = self.conn.recv(1024).decode().strip()
                        if response:
                            break
                    except socket.error as e:
                        if e.errno != errno.EWOULDBLOCK:
                            raise e
                        continue
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
        print(f"[AfterLoginUI] Closing UI for user: {self.identifier} (ID: {self.user_id}), mode: {self.mode}")
        self.running = False

        # For visitors, leave all joined channels before shutting down
        if self.mode == "visitor":
            for channel_id in list(self.joined_channels):  # Create a copy to avoid modifying during iteration
                try:
                    self.conn.sendall(f"LEAVE_CHANNEL {self.user_id} {channel_id}".encode())
                    print(f"[AfterLoginUI] Sent LEAVE_CHANNEL request for channel {channel_id} during logout")
                    # Wait for the response since the socket is non-blocking
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

        # Update status to Offline for authenticated users before shutting down the socket
        if self.mode == "authenticated":
            try:
                self.conn.sendall(f"SET_STATUS {self.user_id} Offline".encode())
                print(f"[AfterLoginUI] Sent SET_STATUS Offline for {self.identifier} (ID: {self.user_id})")
                # Wait for the response since the socket is non-blocking
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

        # Shut down the socket to unblock the listener thread
        try:
            self.conn.shutdown(socket.SHUT_RDWR)
            print(f"[AfterLoginUI] Socket shutdown for {self.identifier} (ID: {self.user_id})")
        except Exception as e:
            print(f"[AfterLoginUI] Error shutting down socket for {self.identifier} (ID: {self.user_id}): {e}")

        # Wait for the listener thread to finish
        try:
            self.listener_thread.join()
            print(f"[AfterLoginUI] Listener thread stopped for {self.identifier} (ID: {self.user_id})")
        except Exception as e:
            print(f"[AfterLoginUI] Error joining listener thread for {self.identifier} (ID: {self.user_id}): {e}")

        # Close the socket
        try:
            self.conn.close()
            print(f"[AfterLoginUI] Socket connection closed for {self.identifier} (ID: {self.user_id})")
        except Exception as e:
            print(f"[AfterLoginUI] Error closing socket for {self.identifier} (ID: {self.user_id}): {e}")

        # Destroy the UI
        self.root.destroy()
        print(f"[AfterLoginUI] UI destroyed for {self.identifier} (ID: {self.user_id})")