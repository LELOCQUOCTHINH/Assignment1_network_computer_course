import socket
import argparse
from multiprocessing import Process
from threading import Thread
from login_ui import LoginUI
from after_login_ui import AfterLoginUI  # Import the new UI
import time

def new_connection(tid, host, port):
    print(f'Process ID {tid} connecting to {host}:{port}')
    client_socket = socket.socket()
    client_socket.connect((host, port))

    def after_login(mode, identifier):
        if mode == "authenticated":
            print(f"Process {tid} logged in as {identifier}")
            # Set status to Online after login
            print(f"Process {tid} sending SET_STATUS {identifier} Online")
            client_socket.sendall(f"SET_STATUS {identifier} Online".encode())
            response = client_socket.recv(1024).decode()
            print(f"Process {tid} received response for SET_STATUS: {response}")
            if response != "STATUS_UPDATED":
                print(f"Failed to set initial status for {identifier}")

        # Launch the AfterLoginUI
        AfterLoginUI(mode, identifier, client_socket)

        # Set status to Offline before disconnecting (unless set to Invisible in UI)
        if mode == "authenticated":
            # Check the current status by querying the server (optional)
            # For simplicity, we'll assume the UI might have set it to Invisible
            print(f"Process {tid} sending SET_STATUS {identifier} Offline")
            client_socket.sendall(f"SET_STATUS {identifier} Offline".encode())
            response = client_socket.recv(1024).decode()
            print(f"Process {tid} received response for SET_STATUS: {response}")

        client_socket.close()

    # Start the UI
    LoginUI(client_socket, after_login)

def connect_server(processnum, host, port):
    """Spawn multiple client processes to connect to the server."""
    processes = [Process(target=new_connection, args=(i, host, port)) for i in range(processnum)]
    [p.start() for p in processes]
    [p.join() for p in processes]  # Wait for all processes to finish

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        prog='Client',
        description='Connect to pre-declare server',
        epilog='!!! It requires the server is running and listening !!!')
    parser.add_argument('--server-ip', help='IP address of the server')
    parser.add_argument('--server-port', type=int, help='Port number of the server')
    parser.add_argument('--client-num', type=int, help='Number of client processes to spawn')
    args = parser.parse_args()
    host = args.server_ip
    port = args.server_port
    cnum = args.client_num
    connect_server(cnum, host, port)