import socket
import threading
import logging
import cv2
import numpy as np
import struct
import time

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class P2PStream:
    def __init__(self, user_id, channel_id, conn, on_frame=None, on_stream_ended=None):
        self.user_id = user_id
        self.channel_id = channel_id
        self.conn = conn
        self.on_frame = on_frame
        self.on_stream_ended = on_stream_ended
        self.running = False
        self.streaming = False
        self.server_socket = None
        self.clients = []
        self.clients_lock = threading.Lock()
        self.stream_port = None
        self.active_streams = {}  # streamer_id -> (client_socket, receive_thread, is_socket_open)
        self.active_streams_lock = threading.Lock()  # Lock for active_streams access
        self.last_frame = None
        self.stream_thread = None
        self.accept_thread = None
        self.cap = None  # Track VideoCapture explicitly

    def get_local_ip(self):
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.settimeout(0)
            s.connect(('8.8.8.8', 1))
            local_ip = s.getsockname()[0]
            s.close()
            logging.info(f"[P2PStream] Determined local IP: {local_ip}")
            return local_ip
        except Exception as e:
            logging.error(f"[P2PStream] Error determining local IP: {e}")
            return "127.0.0.1"

    def start_streaming(self, host=None):
        if self.streaming:
            logging.warning("[P2PStream] Already streaming")
            return
        self.streaming = True
        self.running = True
        try:
            if host is None:
                host = self.get_local_ip()
            self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.server_socket.bind((host, 0))
            self.server_socket.listen(5)
            self.stream_port = self.server_socket.getsockname()[1]
            logging.info(f"[P2PStream] Streaming server started on {host}:{self.stream_port}")
            logging.info(f"[P2PStream] Server socket is listening at {self.server_socket.getsockname()}")

            msg = f"START_STREAM {self.user_id} {self.channel_id} {host} {self.stream_port}"
            self.conn.sendall(msg.encode())
            logging.info(f"[P2PStream] Sent START_STREAM for user {self.user_id}")

            self.stream_thread = threading.Thread(target=self.stream_video, daemon=True)
            self.accept_thread = threading.Thread(target=self.accept_viewers, daemon=True)
            self.stream_thread.start()
            self.accept_thread.start()
        except Exception as e:
            logging.error(f"[P2PStream] Error starting stream: {e}")
            self.stop_streaming()

    def stream_video(self):
        try:
            self.cap = cv2.VideoCapture(0)
            if not self.cap.isOpened():
                logging.error("[P2PStream] Failed to open webcam")
                return

            ret, frame = self.cap.read()
            if not ret:
                logging.error("[P2PStream] Initial frame capture failed. Camera may be in use or inaccessible.")
                return

            logging.info("[P2PStream] Successfully started capturing video")
            time.sleep(1.0)

            while self.streaming:
                ret, frame = self.cap.read()
                if not ret:
                    logging.error("[P2PStream] Failed to capture frame")
                    time.sleep(0.1)
                    continue

                frame = cv2.resize(frame, (320, 240))
                frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

                self.last_frame = frame.copy()
                if self.on_frame:
                    self.on_frame(self.user_id, self.last_frame)

                encoded, buffer = cv2.imencode('.jpg', frame, [int(cv2.IMWRITE_JPEG_QUALITY), 80])
                if not encoded:
                    logging.error("[P2PStream] Failed to encode frame")
                    continue

                frame_data = buffer.tobytes()
                frame_size = len(frame_data)

                with self.clients_lock:
                    clients_to_remove = []
                    for client in self.clients[:]:
                        try:
                            client.sendall(struct.pack('!I', frame_size))
                            client.sendall(frame_data)
                            logging.debug(f"[P2PStream] Sent frame of size {frame_size} to client")
                        except Exception as e:
                            logging.error(f"[P2PStream] Error sending frame to client: {e}")
                            clients_to_remove.append(client)
                            client.close()

                    for client in clients_to_remove:
                        if client in self.clients:
                            self.clients.remove(client)

                time.sleep(0.033)

        except Exception as e:
            logging.error(f"[P2PStream] Error in stream_video: {e}")
        finally:
            if self.cap:
                try:
                    self.cap.release()
                    logging.info("[P2PStream] Released VideoCapture resource")
                except Exception as e:
                    logging.error(f"[P2PStream] Error releasing VideoCapture: {e}")
                self.cap = None
            self.stop_streaming()

    def accept_viewers(self):
        while self.running and self.streaming:
            try:
                self.server_socket.settimeout(1.0)
                logging.debug(f"[P2PStream] Waiting for viewer connections on {self.server_socket.getsockname()}")
                client, addr = self.server_socket.accept()
                logging.info(f"[P2PStream] Viewer connected: {addr}")
                with self.clients_lock:
                    self.clients.append(client)
            except socket.timeout:
                continue
            except Exception as e:
                if self.running and self.streaming:
                    logging.error(f"[P2PStream] Error accepting viewer: {e}")
                break
        logging.info("[P2PStream] Stopped accepting viewers")

    def stop_streaming(self):
        if not self.streaming:
            return
        self.streaming = False
        self.running = False

        # Close all client sockets
        with self.clients_lock:
            for client in self.clients:
                try:
                    client.close()
                except Exception as e:
                    logging.error(f"[P2PStream] Error closing client socket: {e}")
            self.clients.clear()

        # Close the server socket
        if self.server_socket:
            try:
                self.server_socket.close()
            except Exception as e:
                logging.error(f"[P2PStream] Error closing server socket: {e}")
            self.server_socket = None

        # Send STOP_STREAM message
        try:
            msg = f"STOP_STREAM {self.user_id} {self.channel_id}"
            self.conn.sendall(msg.encode())
            logging.info(f"[P2PStream] Sent STOP_STREAM for user {self.user_id}")
        except Exception as e:
            logging.error(f"[P2PStream] Error sending STOP_STREAM: {e}")

        # Wait for threads to terminate
        if self.stream_thread and self.stream_thread.is_alive():
            self.stream_thread.join(timeout=1.0)
            logging.info("[P2PStream] Stream thread terminated")
        if self.accept_thread and self.accept_thread.is_alive():
            self.accept_thread.join(timeout=1.0)
            logging.info("[P2PStream] Accept thread terminated")

        # Ensure VideoCapture is released
        if self.cap:
            try:
                self.cap.release()
                logging.info("[P2PStream] Released VideoCapture resource in stop")
            except Exception as e:
                logging.error(f"[P2PStream] Error releasing VideoCapture in stop: {e}")
            self.cap = None

        # Log active threads for diagnostics
        active_threads = threading.enumerate()
        logging.info(f"[P2PStream] Active threads after stop: {[t.name for t in active_threads]}")

        logging.info(f"[P2PStream] Stopped streaming for user {self.user_id}")

    def start_receiving(self, streamer_id, ip, port):
        if streamer_id in self.active_streams:
            logging.warning(f"[P2PStream] Already receiving stream from {streamer_id}")
            return
        client_socket = None
        try:
            client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            client_socket.settimeout(5.0)
            time.sleep(1.0)
            logging.info(f"[P2PStream] Attempting to connect to {ip}:{port} for streamer {streamer_id}")
            client_socket.connect((ip, int(port)))
            logging.info(f"[P2PStream] Connected to streamer {streamer_id} at {ip}:{port}")

            receive_thread = threading.Thread(target=self.receive_stream, args=(streamer_id, client_socket), daemon=True)
            with self.active_streams_lock:
                self.active_streams[streamer_id] = (client_socket, receive_thread, True)  # True indicates socket is open
            receive_thread.start()
        except socket.timeout as e:
            logging.error(f"[P2PStream] Timeout connecting to streamer {streamer_id} at {ip}:{port}: {e}")
            if client_socket:
                client_socket.close()
        except socket.error as e:
            logging.error(f"[P2PStream] Socket error connecting to streamer {ip}:{port}: {e}")
            if client_socket:
                client_socket.close()
        except Exception as e:
            logging.error(f"[P2PStream] Unexpected error connecting to streamer {streamer_id}: {e}")
            if client_socket:
                client_socket.close()
        finally:
            if streamer_id not in self.active_streams:
                logging.info(f"[P2PStream] Failed to start receiving stream from {streamer_id} at {ip}:{port}")

    def stop_receiving(self, streamer_id):
        logging.info(f"[P2PStream] Stopping receiving stream from {streamer_id}")
        with self.active_streams_lock:
            if streamer_id not in self.active_streams:
                logging.warning(f"[P2PStream] No active stream found for {streamer_id}")
                return
            client_socket, receive_thread, is_socket_open = self.active_streams[streamer_id]
            # Close the socket only if it hasn't been closed already
            if is_socket_open:
                try:
                    client_socket.close()
                    logging.info(f"[P2PStream] Closed client socket for {streamer_id}")
                except Exception as e:
                    logging.warning(f"[P2PStream] Error closing client socket for {streamer_id}: {e}")
                # Update the tuple to mark the socket as closed
                self.active_streams[streamer_id] = (client_socket, receive_thread, False)
            else:
                logging.info(f"[P2PStream] Socket for {streamer_id} was already closed")

            # Remove the stream entry
            del self.active_streams[streamer_id]

        # Wait for the receive thread to terminate
        if receive_thread.is_alive():
            receive_thread.join(timeout=1.0)
            logging.info(f"[P2PStream] Receive thread for {streamer_id} terminated")

        if self.on_stream_ended:
            logging.info(f"[P2PStream] Calling on_stream_ended for streamer {streamer_id}")
            self.on_stream_ended(streamer_id)
        logging.info(f"[P2PStream] Stopped receiving stream from {streamer_id}")

    def receive_stream(self, streamer_id, client_socket):
        logging.info(f"[P2PStream] Started receive_stream thread for streamer {streamer_id}")
        try:
            while True:
                with self.active_streams_lock:
                    if streamer_id not in self.active_streams:
                        logging.info(f"[P2PStream] Stream for {streamer_id} stopped, exiting receive loop")
                        break
                    _, _, is_socket_open = self.active_streams[streamer_id]
                    if not is_socket_open:
                        logging.info(f"[P2PStream] Socket for {streamer_id} closed, exiting receive loop")
                        break

                logging.debug(f"[P2PStream] Waiting to receive frame size from {streamer_id}")
                size_data = client_socket.recv(4)
                if len(size_data) != 4:
                    logging.error(f"[P2PStream] Incomplete frame size received from {streamer_id}: {len(size_data)} bytes")
                    break
                frame_size = struct.unpack('!I', size_data)[0]
                logging.debug(f"[P2PStream] Received frame size {frame_size} from {streamer_id}")

                frame_data = b""
                remaining = frame_size
                while remaining > 0:
                    chunk = client_socket.recv(min(remaining, 4096))
                    if not chunk:
                        logging.error(f"[P2PStream] Connection closed while receiving frame from {streamer_id}")
                        break
                    frame_data += chunk
                    remaining -= len(chunk)
                if len(frame_data) != frame_size:
                    logging.error(f"[P2PStream] Incomplete frame data received from {streamer_id}: {len(frame_data)}/{frame_size} bytes")
                    break

                frame_array = np.frombuffer(frame_data, dtype=np.uint8)
                frame = cv2.imdecode(frame_array, cv2.IMREAD_COLOR)
                if frame is None:
                    logging.error(f"[P2PStream] Failed to decode frame from {streamer_id}")
                    continue

                logging.debug(f"[P2PStream] Successfully decoded frame from {streamer_id}, shape: {frame.shape}")
                if self.on_frame:
                    self.on_frame(streamer_id, frame)

        except Exception as e:
            logging.error(f"[P2PStream] Error receiving stream from {streamer_id}: {e}")
        finally:
            logging.info(f"[P2PStream] Cleaning up receive_stream for streamer {streamer_id}")
            # Only close the socket if it hasn't been closed already
            with self.active_streams_lock:
                if streamer_id in self.active_streams:
                    client_socket, receive_thread, is_socket_open = self.active_streams[streamer_id]
                    if is_socket_open:
                        try:
                            client_socket.close()
                            logging.info(f"[P2PStream] Closed client socket for {streamer_id} in receive_stream")
                        except Exception as e:
                            logging.warning(f"[P2PStream] Error closing client socket for {streamer_id} in receive_stream: {e}")
                        # Update the tuple to mark the socket as closed
                        self.active_streams[streamer_id] = (client_socket, receive_thread, False)
                    # Remove the stream entry
                    del self.active_streams[streamer_id]
                    if self.on_stream_ended:
                        logging.info(f"[P2PStream] Calling on_stream_ended for streamer {streamer_id}")
                        self.on_stream_ended(streamer_id)

    def close(self):
        logging.info(f"[P2PStream] Closing P2PStream for user {self.user_id}")
        self.stop_streaming()
        with self.active_streams_lock:
            for streamer_id in list(self.active_streams.keys()):
                self.stop_receiving(streamer_id)
        # Log active threads for diagnostics
        active_threads = threading.enumerate()
        logging.info(f"[P2PStream] Active threads after close: {[t.name for t in active_threads]}")