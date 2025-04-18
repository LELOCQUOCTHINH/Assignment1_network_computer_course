import socket
from threading import Thread
from peer_manager import PeerManager
import json
import os
from datetime import datetime

# Initialize peer tracker
peer_manager = PeerManager()

USER_DB_FILE = 'users.json'
CHANNEL_DB_FILE = 'channels.json'
MESSAGE_DB_FILE = 'messages.json'

def load_users():
    if os.path.exists(USER_DB_FILE):
        if os.path.getsize(USER_DB_FILE) == 0:
            print(f"[Server] Warning: {USER_DB_FILE} is empty. Initializing with empty dictionary.")
            return {"users": {}, "next_user_id": 1}
        try:
            with open(USER_DB_FILE, 'r') as f:
                return json.load(f)
        except json.JSONDecodeError as e:
            print(f"[Server] Error: Invalid JSON in {USER_DB_FILE} - {e}. Initializing with empty dictionary.")
            return {"users": {}, "next_user_id": 1}
    else:
        print(f"[Server] {USER_DB_FILE} not found. Starting with empty dictionary.")
        return {"users": {}, "next_user_id": 1}

def save_users():
    with open(USER_DB_FILE, 'w') as f:
        json.dump(user_db, f)
    print(f"[Server] Saved users to {USER_DB_FILE}")

def load_channels():
    if os.path.exists(CHANNEL_DB_FILE):
        if os.path.getsize(CHANNEL_DB_FILE) == 0:
            print(f"[Server] Warning: {CHANNEL_DB_FILE} is empty. Initializing with empty dictionary.")
            return {"channels": {}, "next_id": 1}
        try:
            with open(CHANNEL_DB_FILE, 'r') as f:
                return json.load(f)
        except json.JSONDecodeError as e:
            print(f"[Server] Error: Invalid JSON in {CHANNEL_DB_FILE} - {e}. Initializing with empty dictionary.")
            return {"channels": {}, "next_id": 1}
    else:
        print(f"[Server] {CHANNEL_DB_FILE} not found. Starting with empty dictionary.")
        return {"channels": {}, "next_id": 1}

def save_channels():
    with open(CHANNEL_DB_FILE, 'w') as f:
        json.dump(channel_db, f)
    print(f"[Server] Saved channels to {CHANNEL_DB_FILE}")

def load_messages():
    if os.path.exists(MESSAGE_DB_FILE):
        if os.path.getsize(MESSAGE_DB_FILE) == 0:
            print(f"[Server] Warning: {MESSAGE_DB_FILE} is empty. Initializing with empty dictionary.")
            return {"messages": {}}
        try:
            with open(MESSAGE_DB_FILE, 'r') as f:
                return json.load(f)
        except json.JSONDecodeError as e:
            print(f"[Server] Error: Invalid JSON in {MESSAGE_DB_FILE} - {e}. Initializing with empty dictionary.")
            return {"messages": {}}
    else:
        print(f"[Server] {MESSAGE_DB_FILE} not found. Starting with empty dictionary.")
        return {"messages": {}}

def save_messages():
    with open(MESSAGE_DB_FILE, 'w') as f:
        json.dump(message_db, f)
    print(f"[Server] Saved messages to {MESSAGE_DB_FILE}")

user_db = load_users()
users = user_db["users"]
next_user_id = user_db["next_user_id"]

channel_db = load_channels()
channels = channel_db["channels"]
channel_id_counter = channel_db["next_id"]

message_db = load_messages()
messages = message_db["messages"]

connected_clients = []
visitor_ids = {}
visitor_statuses = {}  # New dictionary to track visitor statuses

def get_user_id_by_username(username, is_visitor=False):
    if is_visitor:
        return visitor_ids.get(username)
    for user, info in users.items():
        if user == username:
            return info["user_id"]
    return None

def get_username_by_user_id(user_id):
    for username, info in users.items():
        if info["user_id"] == user_id:
            return username
    for username, vid in visitor_ids.items():
        if vid == user_id:
            return username
    return None

def is_visitor(user_id):
    return user_id in visitor_ids.values()

def get_status(user_id):
    username = get_username_by_user_id(user_id)
    if username in users:
        return users[username]["status"]
    elif user_id in visitor_statuses:
        return visitor_statuses[user_id]
    return "Offline"

def broadcast(message, exclude_conn=None):
    print(f"[Server] Broadcasting message: {message}")
    for client_conn, _, client_username, _ in connected_clients:
        if client_conn != exclude_conn:
            try:
                client_conn.sendall(f"{message}\n".encode())
            except:
                print(f"[Server] Failed to send message to {client_username}")

def broadcast_to_channel(channel_id, message, exclude_conn=None):
    if channel_id not in channels:
        return
    members = channels[channel_id]["members"]
    print(f"[Server] Broadcasting to channel {channel_id} (members: {members}): {message}")
    for client_conn, _, client_username, client_user_id in connected_clients:
        if exclude_conn and client_conn == exclude_conn:
            continue
        if client_user_id in members:
            try:
                client_conn.sendall(f"{message}\n".encode())
            except:
                print(f"[Server] Failed to send message to {client_username} in channel {channel_id}")

def handle_visitor(data, conn):
    global next_user_id
    name = data.split()[1]
    visitor_ids[name] = f"v{next_user_id}"
    user_id = visitor_ids[name]
    visitor_statuses[user_id] = "Online"  # Set visitor status to Online
    next_user_id += 1
    user_db["next_user_id"] = next_user_id
    save_users()
    print(f"[Server] Registered visitor {name} with ID {user_id}")
    # Broadcast the visitor's status to other clients
    broadcast(f"STATUS {user_id} Online", exclude_conn=conn)
    return f"WELCOME_VISITOR {name} {user_id}"

def handle_login(data, conn):
    _, username, password = data.split()
    if username in users and users[username]["password"] == password:
        user_id = users[username]["user_id"]
        current_status = users[username]["status"]
        if current_status != "Invisible":
            users[username]["status"] = "Online"
            broadcast(f"STATUS {user_id} Online", exclude_conn=conn)
        else:
            print(f"[Server] Retaining Invisible status for {username} (ID: {user_id}) on login")
        save_users()
        print(f"[Server] Login successful for {username} (ID: {user_id}), status: {users[username]['status']}")
        return f"LOGIN_SUCCESS {user_id}"
    print(f"[Server] Login failed for {username}")
    return "LOGIN_FAILED"

def handle_register(data):
    global next_user_id
    _, username, password = data.split()
    if username in users:
        print(f"[Server] Username {username} already taken")
        return "USERNAME_TAKEN"
    users[username] = {
        "password": password,
        "status": "Offline",
        "user_id": str(next_user_id)
    }
    next_user_id += 1
    user_db["users"] = users
    user_db["next_user_id"] = next_user_id
    save_users()
    print(f"[Server] Registered new user {username} with ID {users[username]['user_id']}")
    return "REGISTER_SUCCESS"

def handle_get_username(data):
    _, user_id = data.split()
    username = get_username_by_user_id(user_id)
    if username:
        print(f"[Server] Username request for user_id {user_id}: found username {username}")
        return f"USERNAME {user_id} {username}"
    print(f"[Server] Username request for user_id {user_id}: not found")
    return f"USERNAME_NOT_FOUND {user_id}"

def handle_get_status(data):
    _, user_id = data.split()
    status = get_status(user_id)
    print(f"[Server] Status request for user_id {user_id}: {status}")
    return f"STATUS {user_id} {status}"

def handle_set_status(data, addr, conn):
    _, user_id, status = data.split()
    username = get_username_by_user_id(user_id)
    if is_visitor(user_id):
        # Handle visitor status
        if user_id in visitor_statuses:
            if status in ["Online", "Offline", "Invisible"]:
                visitor_statuses[user_id] = status
                print(f"[Server] Set status of visitor {username} (ID: {user_id}) to {status}")
                # Broadcast the status change to other clients
                broadcast(f"STATUS {user_id} {status}", exclude_conn=conn)
                return "STATUS_UPDATED"
            else:
                print(f"[Server] Invalid status {status} for visitor ID {user_id}")
                return "INVALID_STATUS"
        print(f"[Server] Visitor ID {user_id} not found for status update")
        return "USER_NOT_FOUND"
    else:
        # Handle authenticated user status
        if username and username in users:
            if status in ["Online", "Offline", "Invisible"]:
                users[username]["status"] = status
                save_users()
                print(f"[Server] Set status of {username} (ID: {user_id}) to {status}")
                # Broadcast the status change to other clients
                broadcast(f"STATUS {user_id} {status}", exclude_conn=conn)
                return "STATUS_UPDATED"
            else:
                print(f"[Server] Invalid status {status} for user ID {user_id}")
                return "INVALID_STATUS"
        print(f"[Server] User ID {user_id} not found for status update")
        return "USER_NOT_FOUND"

def handle_get_peers(data, addr):
    peers = peer_manager.get_peers()
    peers = [peer for peer in peers if peer != addr]
    
    visible_peers = []
    for ip, port in peers:
        username = None
        for user, info in users.items():
            if "client_addr" in info and info["client_addr"] == f"{ip}:{port}":
                username = user
                break
        if username and users[username]["status"] != "Invisible":
            visible_peers.append((ip, port))
    
    peer_list = " ".join(f"{ip}" for ip, _ in visible_peers)
    print(f"[Server] Sending peer list to {addr}: {peer_list}")
    return f"PEER_LIST {peer_list}" if peer_list else "PEER_LIST"

def handle_create_channel(data):
    global channel_id_counter
    _, user_id, channel_name = data.split(maxsplit=2)
    channel_id = str(channel_id_counter)
    channels[channel_id] = {
        "name": channel_name,
        "host": user_id,
        "members": [user_id]
    }
    channel_id_counter += 1
    channel_db["channels"] = channels
    channel_db["next_id"] = channel_id_counter
    save_channels()
    broadcast(f"UPDATE_CHANNELS {channel_id} {channel_name} {user_id}")
    print(f"[Server] Created channel ID {channel_id} with name '{channel_name}', host={user_id}")
    return f"CHANNEL_CREATED {channel_id}"

def handle_join_channel(data):
    _, user_id, channel_id = data.split()
    if channel_id in channels:
        if user_id not in channels[channel_id]["members"]:
            username = get_username_by_user_id(user_id)
            if not username:
                print(f"[Server] Invalid user_id {user_id} for join request on channel {channel_id}")
                return "USER_NOT_FOUND"
            channels[channel_id]["members"].append(user_id)
            channel_db["channels"] = channels
            save_channels()
            broadcast(f"UPDATE_CHANNELS {channel_id} {channels[channel_id]['name']} {channels[channel_id]['host']}")
            print(f"[Server] User ID {user_id} joined channel {channel_id}")
            return "JOIN_SUCCESS"
        else:
            print(f"[Server] User ID {user_id} is already a member of channel {channel_id}")
            return "ALREADY_MEMBER"
    print(f"[Server] Channel {channel_id} not found for join request by user ID {user_id}")
    return "CHANNEL_NOT_FOUND"

def handle_leave_channel(data):
    _, user_id, channel_id = data.split()
    if channel_id not in channels:
        print(f"[Server] Channel {channel_id} not found for leave request by user ID {user_id}")
        return "CHANNEL_NOT_FOUND"
    if user_id not in channels[channel_id]["members"]:
        print(f"[Server] User ID {user_id} is not a member of channel {channel_id}")
        return "NOT_A_MEMBER"
    if user_id == channels[channel_id]["host"]:
        print(f"[Server] User ID {user_id} is the host of channel {channel_id} and cannot leave")
        return "HOST_CANNOT_LEAVE"
    channels[channel_id]["members"].remove(user_id)
    channel_db["channels"] = channels
    save_channels()
    broadcast(f"UPDATE_CHANNELS {channel_id} {channels[channel_id]['name']} {channels[channel_id]['host']}")
    print(f"[Server] User ID {user_id} left channel {channel_id}")
    return "LEAVE_SUCCESS"

def handle_get_channels(data):
    if not channels:
        print("[Server] No channels exist, responding with NO_CHANNELS")
        return "NO_CHANNELS"
    response = []
    for channel_id, channel in channels.items():
        members = channel["members"]
        visitor_members = [member for member in members if is_visitor(member)]
        regular_members = [member for member in members if not is_visitor(member)]
        num_visitors = len(visitor_members)
        num_regulars = len(regular_members)
        visitor_members_str = " ".join(visitor_members) if visitor_members else ""
        regular_members_str = " ".join(regular_members) if regular_members else ""
        channel_message = (f"CHANNEL {channel_id} {channel['host']} {len(members)} {channel['name']} "
                          f"{num_visitors} {visitor_members_str} {num_regulars} {regular_members_str}")
        response.append(channel_message)
        print(f"[Server] Sending channel info: {channel_message}")
    return "\n".join(response)

def handle_send_message(data, conn):
    _, user_id, channel_id, message = data.split(maxsplit=3)
    if is_visitor(user_id):
        username = get_username_by_user_id(user_id)
        print(f"[Server] Visitor {username} (ID: {user_id}) attempted to send a message to channel {channel_id}")
        return "VISITOR_NOT_ALLOWED"
    if channel_id not in channels:
        print(f"[Server] Channel {channel_id} not found for message from user ID {user_id}")
        return "CHANNEL_NOT_FOUND"
    if user_id not in channels[channel_id]["members"]:
        print(f"[Server] User ID {user_id} is not a member of channel {channel_id}")
        return "NOT_A_MEMBER"
    
    timestamp = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S")
    if channel_id not in messages:
        messages[channel_id] = []
    messages[channel_id].append({
        "user_id": user_id,
        "message": message,
        "timestamp": timestamp
    })
    message_db["messages"] = messages
    save_messages()
    print(f"[Server] Stored message in channel {channel_id} from user ID {user_id}: {message}")
    
    broadcast_to_channel(channel_id, f"MESSAGE {channel_id} {user_id} {timestamp} | {message}")
    return "MESSAGE_SENT"

def handle_get_messages(data):
    _, channel_id = data.split()
    if channel_id not in channels:
        print(f"[Server] Channel {channel_id} not found for message retrieval")
        return "CHANNEL_NOT_FOUND"
    if channel_id not in messages or not messages[channel_id]:
        print(f"[Server] No messages in channel {channel_id}")
        return "NO_MESSAGES"
    response = []
    for msg in messages[channel_id]:
        response.append(f"MESSAGE {channel_id} {msg['user_id']} {msg['timestamp']} | {msg['message']}")
    print(f"[Server] Retrieved messages for channel {channel_id}: {len(response)} messages")
    return "\n".join(response)

def process_command(data, addr, conn):
    print(f"[Server] Processing command from {addr}: {data}")
    if data.startswith("VISITOR"):
        return handle_visitor(data, conn)
    elif data.startswith("LOGIN"):
        return handle_login(data, conn)
    elif data.startswith("REGISTER"):
        return handle_register(data)
    elif data.startswith("GET_USERNAME"):
        return handle_get_username(data)
    elif data.startswith("GET_STATUS"):
        return handle_get_status(data)
    elif data.startswith("SET_STATUS"):
        return handle_set_status(data, addr, conn)
    elif data.startswith("GET_PEERS"):
        return handle_get_peers(data, addr)
    elif data.startswith("CREATE_CHANNEL"):
        return handle_create_channel(data)
    elif data.startswith("JOIN_CHANNEL"):
        return handle_join_channel(data)
    elif data.startswith("LEAVE_CHANNEL"):
        return handle_leave_channel(data)
    elif data.startswith("GET_CHANNELS"):
        return handle_get_channels(data)
    elif data.startswith("SEND_MESSAGE"):
        return handle_send_message(data, conn)
    elif data.startswith("GET_MESSAGES"):
        return handle_get_messages(data)
    else:
        print(f"[Server] Invalid command from {addr}: {data}")
        return "INVALID_COMMAND"

def handle_client_messages(conn, addr, username=None, user_id=None):
    try:
        while True:
            data = conn.recv(1024).decode()
            if not data:
                print(f"[Server] Peer {addr} disconnected gracefully")
                break
            print(f"[Server] Message from {addr}: {data}")
            response = process_command(data, addr, conn)
            if data.startswith("LOGIN") and response.startswith("LOGIN_SUCCESS"):
                username = data.split()[1]
                user_id = response.split()[1]
                connected_clients.append((conn, addr, username, user_id))
                users[username]["client_addr"] = f"{addr[0]}:{addr[1]}"
                save_users()
                print(f"[Server] Added {username} (ID: {user_id}) to connected clients")
            elif data.startswith("VISITOR"):
                username = data.split()[1]
                user_id = response.split()[2]
                connected_clients.append((conn, addr, username, user_id))
                print(f"[Server] Added visitor {username} (ID: {user_id}) to connected clients")
            conn.sendall(f"{response}\n".encode())
    except ConnectionResetError:
        print(f"[Server] Peer {addr} disconnected abruptly")
    except Exception as e:
        print(f"[Server] Error handling client {addr}: {e}")
    finally:
        if username and user_id:
            print(f"[Server] Client {username} (ID: {user_id}) is disconnecting. Processing cleanup...")
            if not is_visitor(user_id):
                # Handle authenticated user
                if username in users:
                    if "client_addr" in users[username]:
                        del users[username]["client_addr"]
                        save_users()
            else:
                # Handle visitor
                print(f"[Server] Visitor {username} (ID: {user_id}) is logging out. Removing from channels...")
                channels_updated = False
                for channel_id, channel in channels.items():
                    if user_id in channel["members"]:
                        channel["members"].remove(user_id)
                        channels_updated = True
                        print(f"[Server] Removed visitor {username} (ID: {user_id}) from channel {channel_id} ({channel['name']})")
                        broadcast(f"UPDATE_CHANNELS {channel_id} {channel['name']} {channel['host']}")
                if channels_updated:
                    channel_db["channels"] = channels
                    save_channels()
                    print(f"[Server] Updated channels.json after removing visitor {username} (ID: {user_id})")
                else:
                    print(f"[Server] No channels updated for visitor {username} (ID: {user_id}) - they were not in any channels")
                # Remove the visitor from visitor_ids and visitor_statuses
                visitor_name = None
                for name, vid in list(visitor_ids.items()):
                    if vid == user_id:
                        visitor_name = name
                        break
                if visitor_name:
                    del visitor_ids[visitor_name]
                    print(f"[Server] Removed visitor {visitor_name} (ID: {user_id}) from visitor_ids")
                else:
                    print(f"[Server] Visitor ID {user_id} not found in visitor_ids during cleanup")
                if user_id in visitor_statuses:
                    del visitor_statuses[user_id]
                    print(f"[Server] Removed visitor {username} (ID: {user_id}) from visitor_statuses")
                    broadcast(f"STATUS {user_id} Offline", exclude_conn=conn)
        if (conn, addr, username, user_id) in connected_clients:
            connected_clients.remove((conn, addr, username, user_id))
            print(f"[Server] Removed {username} (ID: {user_id}) from connected clients")
        peer_manager.remove_peer(addr)
        conn.close()

def new_connection(conn, addr):
    peer_manager.add_peer(addr)
    handle_client_messages(conn, addr)


def get_host_default_interface_ip(): #get server IP
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    #create a UDP connection because we're not actually sending data,
    #we just want to retrieve the server's IP from this connection
    try:
       s.connect(('8.8.8.8',1)) #try connecting to google (8.8.8.8 is google's public DNS server)
       ip = s.getsockname()[0] #a trick to retrieve server's IP from the connection between google and server
    except Exception:
       ip = '127.0.0.1' #if the trick fails (no internet/offline or google's incident), it falls back to 127.0.0.1
    finally:
       s.close() #close the socket to avoid leaking resource
    return ip


def server_program(host, port): #the server's program
    serversocket = socket.socket() #create a TCP connection
    serversocket.bind((host, port)) #binds it to (host, port)

    serversocket.listen(10) #Listens for connection with a backlog of 10 (just accept 10 clients at a time)
    while True:
        conn, addr = serversocket.accept() #blocking commands, the program will be blocked until a connection to this socket happen
        #accept connection to this socket
        nconn = Thread(target=new_connection, args=(conn, addr)) #method is new_connection, arguments is conn, addr
        #spawning a new thread per client (to support multi-connection) and execute new_connection method
        nconn.start()


if __name__ == "__main__":
    #hostname = socket.gethostname()
    hostip = get_host_default_interface_ip() #return the server IP
    port = 22236 #using port 22236 on server IP
    print("Listening on: {}:{}".format(hostip,port)) #print out server IP and Port
    server_program(hostip, port) #run server's program with server's IP and port
