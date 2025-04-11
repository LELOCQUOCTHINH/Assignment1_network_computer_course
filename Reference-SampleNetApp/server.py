import socket
from threading import Thread
from peer_manager import PeerManager
import json
import os

# Initialize peer tracker
peer_manager = PeerManager()

USER_DB_FILE = 'users.json'
CHANNEL_DB_FILE = 'channels.json'

def load_users():
    if os.path.exists(USER_DB_FILE):
        if os.path.getsize(USER_DB_FILE) == 0:
            print(f"Warning: {USER_DB_FILE} is empty. Initializing with empty dictionary.")
            return {"users": {}, "next_user_id": 1}
        try:
            with open(USER_DB_FILE, 'r') as f:
                return json.load(f)
        except json.JSONDecodeError as e:
            print(f"Error: Invalid JSON in {USER_DB_FILE} - {e}. Initializing with empty dictionary.")
            return {"users": {}, "next_user_id": 1}
    else:
        print(f"{USER_DB_FILE} not found. Starting with empty dictionary.")
        return {"users": {}, "next_user_id": 1}

def save_users():
    with open(USER_DB_FILE, 'w') as f:
        json.dump(user_db, f)
        print(f"Saved users to {USER_DB_FILE}")

def load_channels():
    if os.path.exists(CHANNEL_DB_FILE):
        if os.path.getsize(CHANNEL_DB_FILE) == 0:
            print(f"Warning: {CHANNEL_DB_FILE} is empty. Initializing with empty dictionary.")
            return {"channels": {}, "next_id": 1}
        try:
            with open(CHANNEL_DB_FILE, 'r') as f:
                return json.load(f)
        except json.JSONDecodeError as e:
            print(f"Error: Invalid JSON in {CHANNEL_DB_FILE} - {e}. Initializing with empty dictionary.")
            return {"channels": {}, "next_id": 1}
    else:
        print(f"{CHANNEL_DB_FILE} not found. Starting with empty dictionary.")
        return {"channels": {}, "next_id": 1}

def save_channels():
    with open(CHANNEL_DB_FILE, 'w') as f:
        json.dump(channel_db, f)
        print(f"Saved channels to {CHANNEL_DB_FILE}")

user_db = load_users()
users = user_db["users"]  # {username: {"password": password, "status": status, "user_id": user_id, "client_addr": client_addr}}
next_user_id = user_db["next_user_id"]  # Auto-incrementing user ID

channel_db = load_channels()
channels = channel_db["channels"]  # {channel_id: {"name": name, "host": user_id, "members": [user_ids]}}
channel_id_counter = channel_db["next_id"]  # Auto-incrementing Channel ID

# List to keep track of connected clients (conn, addr, username, user_id)
connected_clients = []
visitor_ids = {}  # {username: user_id} for visitors

def get_user_id_by_username(username, is_visitor=False):
    """Get the user_id for a given username, distinguishing between authenticated users and visitors."""
    if is_visitor:
        return visitor_ids.get(username)
    for user, info in users.items():
        if user == username:
            return info["user_id"]
    return None

def get_username_by_user_id(user_id):
    """Get the username for a given user_id, checking both authenticated users and visitors."""
    # Check authenticated users
    for username, info in users.items():
        if info["user_id"] == user_id:
            return username
    # Check visitors
    for username, vid in visitor_ids.items():
        if vid == user_id:
            return username
    return None

def broadcast(message, exclude_conn=None):
    """Broadcast a message to all clients except the excluded one."""
    for client_conn, _, client_username, _ in connected_clients:
        if client_conn != exclude_conn:
            try:
                client_conn.sendall(message.encode())
            except:
                print(f"Failed to send message to {client_username}")

def handle_visitor(data):
    global next_user_id
    name = data.split()[1]
    # Assign a temporary user_id to the visitor
    visitor_ids[name] = f"v{next_user_id}"
    next_user_id += 1
    user_db["next_user_id"] = next_user_id
    save_users()
    return f"WELCOME_VISITOR {name} {visitor_ids[name]}"

def handle_login(data):
    _, username, password = data.split()
    if username in users and users[username]["password"] == password:
        users[username]["status"] = "Online"
        save_users()
        return f"LOGIN_SUCCESS {users[username]['user_id']}"
    return "LOGIN_FAILED"

def handle_register(data):
    global next_user_id
    _, username, password = data.split()
    if username in users:
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
    return "REGISTER_SUCCESS"

def handle_set_status(data, addr):
    _, user_id, status = data.split()
    # Find the username by user_id
    username = get_username_by_user_id(user_id)
    if username and username in users:  # Only authenticated users can set status
        if status in ["Online", "Offline", "Invisible"]:
            users[username]["status"] = status
            save_users()
            print(f"Set status of {username} (ID: {user_id}) to {status}")
            return "STATUS_UPDATED"
        else:
            return "INVALID_STATUS"
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
    # Broadcast to all clients to update their channel lists
    username = get_username_by_user_id(user_id)
    broadcast(f"UPDATE_CHANNELS {channel_id} {channel_name} {user_id}")
    return f"CHANNEL_CREATED {channel_id}"

def handle_join_channel(data):
    _, user_id, channel_id = data.split()
    if channel_id in channels:
        if user_id not in channels[channel_id]["members"]:
            channels[channel_id]["members"].append(user_id)
            channel_db["channels"] = channels
            save_channels()
            # Broadcast to update channel lists for all clients
            broadcast(f"UPDATE_CHANNELS {channel_id} {channels[channel_id]['name']} {channels[channel_id]['host']}")
            return "JOIN_SUCCESS"
        else:
            return "ALREADY_MEMBER"
    return "CHANNEL_NOT_FOUND"

def handle_get_channels(data):
    if not channels:
        return "NO_CHANNELS"
    response = []
    for channel_id, channel in channels.items():
        members = " ".join(channel["members"])
        response.append(f"CHANNEL {channel_id} {channel['name']} {channel['host']} {members}")
    return "\n".join(response)

def process_command(data, addr, conn):
    if data.startswith("VISITOR"):
        return handle_visitor(data)
    elif data.startswith("LOGIN"):
        return handle_login(data)
    elif data.startswith("REGISTER"):
        return handle_register(data)
    elif data.startswith("SET_STATUS"):
        return handle_set_status(data, addr)
    elif data.startswith("GET_PEERS"):
        return handle_get_peers(data, addr)
    elif data.startswith("CREATE_CHANNEL"):
        return handle_create_channel(data)
    elif data.startswith("JOIN_CHANNEL"):
        return handle_join_channel(data)
    elif data.startswith("GET_CHANNELS"):
        return handle_get_channels(data)
    else:
        return "INVALID_COMMAND"

def handle_client_messages(conn, addr, username=None, user_id=None):
    try:
        while True:
            data = conn.recv(1024).decode()
            if not data:
                print(f"Peer {addr} disconnected gracefully")
                break
            print(f"Message from {addr}: {data}")
            response = process_command(data, addr, conn)
            # Track the username and user_id after a successful login or visitor connection
            if data.startswith("LOGIN") and response.startswith("LOGIN_SUCCESS"):
                username = data.split()[1]
                user_id = response.split()[1]
                connected_clients.append((conn, addr, username, user_id))
                users[username]["client_addr"] = f"{addr[0]}:{addr[1]}"
                save_users()
            elif data.startswith("VISITOR"):
                username = data.split()[1]
                user_id = response.split()[2]  # WELCOME_VISITOR name user_id
                connected_clients.append((conn, addr, username, user_id))
            conn.sendall(response.encode())
    except ConnectionResetError:
        print(f"Peer {addr} disconnected abruptly")
    except Exception as e:
        print(f"Error handling client {addr}: {e}")
    finally:
        if username and user_id:
            if username in users:  # Authenticated user
                if users[username]["status"] != "Invisible":
                    users[username]["status"] = "Offline"
                    save_users()
                    print(f"Set status of {username} (ID: {user_id}) to Offline")
                if "client_addr" in users[username]:
                    del users[username]["client_addr"]
                    save_users()
            elif username in visitor_ids:  # Visitor
                del visitor_ids[username]
        if (conn, addr, username, user_id) in connected_clients:
            connected_clients.remove((conn, addr, username, user_id))
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
