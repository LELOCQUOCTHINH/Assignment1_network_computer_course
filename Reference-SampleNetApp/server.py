import socket
from threading import Thread
from peer_manager import PeerManager
import json
import os

# Initialize peer tracker
peer_manager = PeerManager()

USER_DB_FILE = 'users.json'

def load_users():
    if os.path.exists(USER_DB_FILE):
        if os.path.getsize(USER_DB_FILE) == 0:
            print(f"Warning: {USER_DB_FILE} is empty. Initializing with empty dictionary.")
            return {}
        try:
            with open(USER_DB_FILE, 'r') as f:
                return json.load(f)
        except json.JSONDecodeError as e:
            print(f"Error: Invalid JSON in {USER_DB_FILE} - {e}. Initializing with empty dictionary.")
            return {}
    else:
        print(f"{USER_DB_FILE} not found. Starting with empty dictionary.")
        return {}

def save_users():
    with open(USER_DB_FILE, 'w') as f:
        json.dump(users, f)
        print(f"Saved users to {USER_DB_FILE}")

users = load_users()

def handle_visitor(data):
    name = data.split()[1]
    return f"WELCOME_VISITOR {name}"

def handle_login(data):
    _, username, password = data.split()
    if username in users and users[username]["password"] == password:
        users[username]["status"] = "Online"  # Set status to Online on login
        save_users()
        return "LOGIN_SUCCESS"
    return "LOGIN_FAILED"

def handle_register(data):
    _, username, password = data.split()
    if username in users:
        return "USERNAME_TAKEN"
    users[username] = {"password": password, "status": "Offline"}  # Initialize status as Offline
    save_users()
    return "REGISTER_SUCCESS"

def handle_set_status(data, addr):
    _, username, status = data.split()
    if username in users:
        if status in ["Online", "Offline", "Invisible"]:
            users[username]["status"] = status
            save_users()
            print(f"Set status of {username} to {status}")
            return "STATUS_UPDATED"
        else:
            return "INVALID_STATUS"
    return "USER_NOT_FOUND"

def handle_get_peers(data, addr):
    # Get the list of connected peers
    peers = peer_manager.get_peers()
    peers = [peer for peer in peers if peer != addr]
    
    # Filter out peers whose users are in Invisible mode
    visible_peers = []
    for ip, port in peers:
        # Find the username associated with this peer (if any)
        username = None
        for user, info in users.items():
            if "client_addr" in info and info["client_addr"] == f"{ip}:{port}":
                username = user
                break
        # Include the peer only if the user is not Invisible
        if username and users[username]["status"] != "Invisible":
            visible_peers.append((ip, port))
    
    peer_list = " ".join(f"{ip}" for ip, _ in visible_peers)
    return f"PEER_LIST {peer_list}" if peer_list else "PEER_LIST"

def process_command(data, addr):
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
    else:
        return "INVALID_COMMAND"

def handle_client_messages(conn, addr, username=None):
    try:
        while True:
            data = conn.recv(1024).decode()
            if not data:
                print(f"Peer {addr} disconnected gracefully")
                break
            print(f"Message from {addr}: {data}")
            response = process_command(data, addr)
            # Track the username and client address after a successful login
            if data.startswith("LOGIN") and response == "LOGIN_SUCCESS":
                username = data.split()[1]
                # Store the client address in the user database
                users[username]["client_addr"] = f"{addr[0]}:{addr[1]}"
                save_users()
            conn.sendall(response.encode())
    except ConnectionResetError:
        print(f"Peer {addr} disconnected abruptly")
    except Exception as e:
        print(f"Error handling client {addr}: {e}")
    finally:
        # Update user status to Offline on disconnect (if not Invisible)
        if username and username in users:
            if users[username]["status"] != "Invisible":
                users[username]["status"] = "Offline"
                save_users()
                print(f"Set status of {username} to Offline")
            # Remove the client address
            if "client_addr" in users[username]:
                del users[username]["client_addr"]
                save_users()
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
