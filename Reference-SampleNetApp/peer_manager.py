class PeerManager:
    def __init__(self):
        self.peers = {}  # Format: {addr: (ip, port)}

    def add_peer(self, addr):
        """Add a peer to the directory."""
        ip, port = addr
        self.peers[addr] = (ip, port)
        print(f"Added peer {addr} to directory")

    def remove_peer(self, addr):
        """Remove a peer from the directory."""
        if addr in self.peers:
            del self.peers[addr]
            print(f"Removed peer {addr} from directory")

    def get_peers(self):
        """Return the list of peers."""
        return [(ip, port) for (addr, (ip, port)) in self.peers.items()]