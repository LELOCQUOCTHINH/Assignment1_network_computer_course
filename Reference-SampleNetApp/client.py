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

    def after_login(mode, identifier, user_id):
        # Launch AfterLoginUI with the provided user_id
        if user_id:
            AfterLoginUI(mode, identifier, user_id, client_socket)
        else:
            print(f"Failed to obtain user_id for {identifier}. Cannot launch AfterLoginUI.")

    login_ui = LoginUI(client_socket, after_login)
    login_ui.root.mainloop()

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