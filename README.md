# Segment Chat Application - Assignment 1 README

## Overview
This project implements a hybrid P2P and client-server based Segment Chat application, similar to Discord, as part of the **Computer Networks** course (Semester 2, 2024-2025). The application supports user authentication, channel management, text messaging, and live streaming, leveraging both client-server and peer-to-peer paradigms. It meets the requirements outlined in the assignment, including tracker protocol, data synchronization, and connection logging.

---

## Application Features and Functions

### 1. Hybrid Paradigm
- **Client-Server Paradigm**: Used for user authentication, channel management, and message synchronization.
- **Peer-to-Peer Paradigm**: Facilitates live streaming between peers, reducing server load during high-traffic scenarios.

### 2. Authentication
- **Visitor Mode**:
  - No login required; users provide a name to join as a visitor.
  - View-only permissions; cannot send messages or create channels.
- **Authenticated User Mode**:
  - Requires username and password for login.
  - Full permissions to create/edit content, manage channels, and stream.
  - Supports status modes: **Online**, **Offline**, and **Invisible**.

### 3. Channel Management
- **Channel Creation**: Authenticated users can create channels (stored locally and synced with the centralized server).
- **Join/Leave Channels**: Users can join or leave channels; visitors can join but have limited permissions.
- **Channel Hosting**: Channels created by a user are hosted on their peer, with a backup on the centralized server.
- **Message Display**: Each channel has a scrollable message list with timestamps and usernames.

### 4. Messaging
- Authenticated users can send messages in channels they’ve joined.
- Messages are synchronized between the channel host and the centralized server.
- Visitors cannot send messages.

### 5. Live Streaming
- Authenticated users can start a live stream in a channel using P2P connections.
- Other users in the channel can view the stream directly from the streamer’s peer.
- The centralized server is used for stream coordination (e.g., notifying users of stream start/stop).

### 6. Synchronization
- **Channel Hosting Sync**:
  - When a channel host goes online, local content is synced with the centralized server.
  - New content is synchronized in real-time during online sessions.
- **Offline Scenarios**:
  - If the channel host is offline, joined users fetch content from the centralized server.
  - Visitors and authenticated users can still view cached content.

### 7. Connection Logging
- Logs connection events, messages, and stream activities in `connection_log.txt`.
- Rotates the log file when it exceeds 10,000 records.

---

## Architecture and Design

### Main Classes
- **`server.py`**: Centralized server handling user authentication, channel management, message storage, and stream coordination.
  - Key Functions: `handle_login`, `handle_create_channel`, `handle_send_message`, `handle_start_stream`.
- **`client.py`**: Entry point for spawning client processes, connecting to the server, and launching the UI.
- **`login_ui.py`**: Implements the login interface for visitor and authenticated modes.
- **`after_login_ui.py`**: Main UI for channel interaction, messaging, and streaming.
- **`p2p_stream.py`**: Manages P2P video streaming using OpenCV for webcam capture and socket programming for data transfer.

### Class Diagram
```
+----------------+       +----------------+       +----------------+
|    server.py   |<----->|    client.py   |<----->|  login_ui.py   |
| - PeerManager  |       |- new_connection|       | - LoginUI      |
| - handle_login |       |                |       +----------------+
| - handle_stream|       +----------------+             |
+----------------+                                      v
                                                +----------------+
                                                |after_login_ui.py|
                                                | - AfterLoginUI  |
                                                | - P2PStream     |
                                                +----------------+
                                                        |
                                                +----------------+
                                                |  p2p_stream.py  |
                                                | - P2PStream     |
                                                | - stream_video  |
                                                +----------------+
```

### Communication Flow
1. **Tracker Protocol (Client-Server)**:
   - Client submits its info (`submit_info`) to the server.
   - Server adds the client to the peer list (`add_list`).
   - Client requests the peer list (`get_list`).
   - Client connects to peers directly (`peer_connect`).

2. **Live Streaming (P2P)**:
   - Streamer starts a stream and notifies the server (`START_STREAM`).
   - Server broadcasts the stream info to channel members (`LIVESTREAM_START`).
   - Viewers connect directly to the streamer via P2P and receive video frames.

---

## Communication Protocols

### Tracker Protocol (20%)
- **Purpose**: Initialize peer connections via the centralized server.
- **Messages**:
  - `GET_PEERS`: Client requests the list of peers.
  - `PEER_LIST <ip1> <ip2> ...`: Server responds with a space-separated list of peer IPs.
- **Implementation**: Handled in `server.py` (`handle_get_peers`) and `PeerManager`.

### Client-Server Paradigm (20%)
- **Purpose**: Manage authentication, channels, and messages.
- **Messages**:
  - `LOGIN <username> <password>`: Authenticate a user.
  - `REGISTER <username> <password>`: Register a new user.
  - `VISITOR <name>`: Join as a visitor.
  - `CREATE_CHANNEL <user_id> <channel_name>`: Create a new channel.
  - `SEND_MESSAGE <user_id> <channel_id> <message>`: Send a message.
  - `GET_CHANNELS`: Retrieve the list of channels.
  - `GET_MESSAGES <channel_id>`: Fetch messages for a channel.

### Peer-to-Peer Paradigm (20%)
- **Purpose**: Handle live streaming between peers.
- **Messages**:
  - `START_STREAM <user_id> <channel_id> <ip> <port>`: Notify the server of a new stream.
  - `STOP_STREAM <user_id> <channel_id>`: Stop the stream.
  - **P2P Data Transfer**: Video frames are sent as binary data (frame size in bytes followed by JPEG-encoded frame).
- **Implementation**: `p2p_stream.py` (`stream_video`, `receive_stream`).

---

## Synchronization (10%)
- **Channel Hosting**:
  - Local content on the channel host’s peer is synced with the centralized server when the host goes online.
  - New messages are synced in real-time (`SEND_MESSAGE` updates both local and server storage).
- **Offline Access**:
  - If the channel host is offline, users fetch content from the server (`GET_MESSAGES`).
- **Implementation**: `server.py` (`handle_send_message`, `handle_get_messages`).

---

## Connection Logging (10%)
- **Log File**: `connection_log.txt`.
- **Format**: `[<timestamp>] <event_type> | Source: <source> | Details: <details>`.
- **Events Logged**:
  - `CONNECTION_ESTABLISHED`: New client connection.
  - `MESSAGE_SENT`: Message sent in a channel.
  - `STREAM_START`/`STREAM_STOP`: Streaming events.
  - `NOTIFICATION_SENT`: Broadcast notifications.
- **Rotation**: Logs are rotated when exceeding 10,000 records (`server.py`, `rotate_log_file`).

---

## Advanced Features (10%)
- **Status Management**: Supports Online, Offline, and Invisible modes for authenticated users.
- **Non-Blocking Sockets**: Used in `login_ui.py` and `after_login_ui.py` to handle asynchronous communication.
- **Error Handling**: Robust logging and cleanup for socket errors and stream interruptions (`p2p_stream.py`).

---

## Validation and Performance
- **Sanity Tests**:
  - **Authentication**: Successfully logged in as both visitor and authenticated user.
  - **Channel Operations**: Created, joined, and left channels; sent messages.
  - **Streaming**: Started a stream and viewed it from another client.
- **Performance**:
  - **Streaming Latency**: Average latency of 50-100ms for video frames (320x240 resolution, 80% JPEG quality).
  - **Message Sync**: Messages appear in the UI within 200ms of being sent.
  - **Scalability**: Tested with 5 concurrent clients; server handled connections without bottlenecks.

---

## Known Issues
- **Streaming Stability**: Occasional socket errors during stream start/stop; mitigated with retries but not fully resolved.
- **UI Responsiveness**: Message list updates may lag with high message volume due to Tkinter limitations.
- **Visitor Cleanup**: Visitor data persists in channels after logout; requires manual cleanup on the server.

---

## How to Run
1. **Prerequisites**:
   - Python 3.8+
   - Libraries: `tkinter`, `opencv-python`, `numpy`, `Pillow`
   - Install dependencies: `pip install opencv-python numpy Pillow`

2. **Start the Server**:
   ```bash
   python server.py
   ```
   - The server listens on the default IP (determined dynamically) and port `22236`.

3. **Start the Client**:
   ```bash
   python client.py --server-ip <server_ip> --server-port 22236 --client-num <client_num>
   ```
   - Replace `<server_ip>` with the server’s IP address.
   - `<client_num>` specifies the number of client processes to spawn.

4. **Usage**:

   Follow these steps to use the Segment Chat application, from logging in to livestreaming and logging out:

   - **Step 1: Log In**\
     Launch the client, and you’ll see the login window:
     
     ![Login_UI](https://github.com/user-attachments/assets/411259cb-96db-4d88-b776-b66c53232394)
     
     Choose to log in as a visitor by entering a name (e.g., "Guest1") and clicking "Continue as Visitor," or log in as an authenticated user by entering a username and password (or registering a new account).

   - **Step 2: Create or Join a Channel**\
     After logging in, the main UI will appear:

     ![After_login_UI](https://github.com/user-attachments/assets/4bd8e708-3915-4e5d-97e1-c5276f07e187)

     As an authenticated user, you can create a new channel by clicking "Create a New Channel" above the "Hosting channels" section:

     ![create_new_channel](https://github.com/user-attachments/assets/cd76074a-2d34-44dd-827b-32e4e7a9382d)

     Entering a channel name (e.g., "MyChatRoom"), and submitting:

     ![naming_for_channel](https://github.com/user-attachments/assets/cc9fe3a2-07d7-4667-ba80-d37c6201e25b)

     Alternatively, join an existing channel by clicking its name in the "Other channels" section and clicking "Join this channel."

     ![join_a_channel](https://github.com/user-attachments/assets/1d3e3dc5-aebc-4088-b24a-26cf373de22d)

     Note that: after you joined to a channel, you may need to refresh by clicking to the channel name so that view full content of the channel.

   - **Step 3: Start a Livestream**\
     After you have already joined to a channel and logged as authenticated mode, you can live stream by using your webcam (the webcam must be available) or texting at the channel:
          
     ![livesteam](https://github.com/user-attachments/assets/eab6a945-2861-4972-a354-8a0a9c37b18c)

     Following these steps: Select a channel you’ve joined or created. In the channel view, click the "Start Streaming" button to begin a livestream. Other users in the channel will see your stream in real-time. You’ll see your own stream labeled as "Your Stream" in the UI.

   - **Step 4: Log Out**\
     To end your session, click the "LOGOUT" button at the bottom of the sidebar. This will stop any active streams, close your connection, and exit the application.

---

## File Structure
- `server.py`: Centralized server implementation.
- `client.py`: Client entry point for spawning processes.
- `login_ui.py`: Login UI for authentication.
- `after_login_ui.py`: Main UI for chatting and streaming.
- `p2p_stream.py`: P2P streaming logic.
- `connection_log.txt`: Log file for connection events.
- `users.json`, `channels.json`, `messages.json`: Storage for users, channels, and messages.

---

## Conclusion
This Segment Chat application successfully demonstrates the hybrid paradigm, integrating client-server and P2P communication. It fulfills the core requirements of the assignment while adding features like status management and robust logging. Future improvements could focus on enhancing streaming stability and UI performance.
