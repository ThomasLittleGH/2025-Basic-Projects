import shlex
import os
import struct
from socket import socket, SOCK_STREAM, AF_INET
from zlib import compress, decompress
from threading import Thread
from math import ceil
import time

# ============================
# CONFIGURATION & CONSTANTS
# ============================

PORT = 8000
DESTINATION_ADDRESS = input("Target address (xxx.xxx.xxx.xxx, leave empty to wait for connection): ") or None
LOCAL_ADDRESS = ('0.0.0.0', PORT)
BUFFER_SIZE = 1024**2 * 4  # 4MB chunks for efficient transfer
DELIMITER = "#%E&T"

print(f"[DEBUG] PORT: {PORT}")
print(f"[DEBUG] DESTINATION_ADDRESS: {DESTINATION_ADDRESS}")
print(f"[DEBUG] LOCAL_ADDRESS: {LOCAL_ADDRESS}")
print(f"[DEBUG] BUFFER_SIZE: {BUFFER_SIZE}")
print(f"[DEBUG] DELIMITER: {DELIMITER}")

# ============================
# CLASSES: METADATA & PACKETS
# ============================

class Metadata:
    """Handles file metadata for transfer"""

    def __init__(self, name="", size=2):
        self.name = name
        self.size = int(size)
        self.total_packets = ceil(self.size / BUFFER_SIZE)
        print(f"[DEBUG] Initialized Metadata: name={self.name}, size={self.size}, total_packets={self.total_packets}")

    def export(self):
        """Converts metadata to a byte-encoded string"""
        export_str = f"{self.name}{DELIMITER}{self.size}{DELIMITER}{self.total_packets}"
        print(f"[DEBUG] Exporting Metadata: {export_str}")
        return export_str.encode()

    @classmethod
    def import_(cls, byte_data):
        """Creates a Metadata object from a received byte string"""
        data = byte_data.decode().split(DELIMITER)
        print(f"[DEBUG] Importing Metadata from data: {data}")
        return cls(name=data[0], size=int(data[1]))

    def __str__(self):
        return f"[Metadata] Name: {self.name}, Size: {self.size} bytes, Packets: {self.total_packets}"


class Packet:
    """Handles individual file packets for transfer"""

    def __init__(self, identifier, position=0, data=b""):
        self.identifier = identifier
        self.position = int(position)
        self.data = data
        print(f"[DEBUG] Created Packet: ID={self.identifier}, Position={self.position}, DataSize={len(self.data)} bytes")

    def export(self):
        header = f"{self.identifier}{DELIMITER}{self.position}{DELIMITER}".encode()
        payload = header + self.data
        compressed_payload = compress(payload)
        # Pack the length (unsigned int, network byte order) followed by the compressed payload
        packet_length = struct.pack("!I", len(compressed_payload))
        exported = packet_length + compressed_payload
        print(
            f"[DEBUG] Exporting Packet at position {self.position}, Compressed size: {len(compressed_payload)} bytes, Total with length: {len(exported)} bytes")
        return exported

    @classmethod
    def import_(cls, byte_data):
        """Deserializes a received packet"""
        try:
            decompressed = decompress(byte_data)
            parts = decompressed.split(DELIMITER.encode(), 2)
            identifier = parts[0].decode()
            position = int(parts[1].decode())
            data = parts[2]
            print(f"[DEBUG] Imported Packet: ID={identifier}, Position={position}, DataSize={len(data)} bytes")
            return cls(identifier=identifier, position=position, data=data)
        except Exception as e:
            print(f"[ERROR] Failed to import packet: {e}")
            raise

    def get_position(self):
        return self.position

    def get_data(self):
        return self.data

    def __str__(self):
        return f"[Packet] ID: {self.identifier}, Position: {self.position}, Size: {len(self.data)} bytes"


# ============================
# FILE UTILITY FUNCTIONS
# ============================

def handle_file_path():
    """Prompts user for a file path and sanitizes it"""
    fp = input("Enter full file path: ").strip()
    fp = shlex.split(fp)[0]
    fp = os.path.expanduser(fp)
    fp = os.path.normpath(fp)
    print(f"[DEBUG] Resolved File Path: {fp}")
    return fp


def get_metadata_from_file_path(fp) -> Metadata:
    """Extracts metadata from a file path"""
    file_name = os.path.basename(fp)
    file_size = os.path.getsize(fp)
    md = Metadata(name=file_name, size=file_size)
    print(f"[DEBUG] Generated Metadata: {md}")
    return md


def send_packet(position, data) -> Packet:
    """Creates and returns a packet for given position and data"""
    packet = Packet(identifier="FILE", position=position, data=data)
    print(f"[DEBUG] Prepared packet for position {position}")
    return packet


def recv_full(sock, n):
    """Receive exactly n bytes from the socket."""
    data = b""
    while len(data) < n:
        more = sock.recv(n - len(data))
        if not more:
            raise EOFError("Socket closed before we received enough data")
        data += more
    return data

# ============================
# FILE RECEIVER (SERVER)
# ============================

class FileReceiver:
    """Handles file reception (server-side)"""

    def __init__(self, port):
        self.port = port
        print(f"[DEBUG] FileReceiver initialized on port {self.port}")

    def start_server(self):
        """Starts the server and listens for connections"""
        print("[DEBUG] Server: Waiting for connection...")
        with socket(AF_INET, SOCK_STREAM) as server_socket:
            server_socket.bind(LOCAL_ADDRESS)
            server_socket.listen(1)
            sock, addr = server_socket.accept()
            print(f"[DEBUG] Server: Peer connected from {addr}")
            self.receive_file(sock)

    def receive_file(self, sock):
        global progress_path, missing_packets
        try:
            raw_metadata = sock.recv(1024)
            print(f"[DEBUG] Server: Received raw metadata: {raw_metadata}")
            metadata = Metadata.import_(raw_metadata)
            print(f"[DEBUG] Server: Received Metadata: {metadata}")

            progress_path = metadata.name + ".progress"
            if os.path.exists(metadata.name) and not os.path.exists(progress_path):
                print("[ERROR] Server: File already exists and no progress file found.")
                sock.send(b"ERROR: File already exists")
                sock.close()
                return

            missing_packets = set()
            if os.path.exists(progress_path):
                print("[DEBUG] Server: Resuming file upload; progress file exists.")
                with open(progress_path, "r") as progress:
                    missing_packets = set(int(line.strip()) for line in progress.readlines())
                sock.send((f"MISSING_PACKETS{DELIMITER}" + ",".join(map(str, missing_packets))).encode())
                print(f"[DEBUG] Server: Missing packets: {missing_packets}")
            else:
                missing_packets = set(range(metadata.total_packets))
                sock.send(b"START_NEW_TRANSFER")
                with open(progress_path, "w") as progress:
                    for i in range(metadata.total_packets):
                        progress.write(f"{i}\n")
                print(f"[DEBUG] Server: Created progress file with packets: 0 to {metadata.total_packets - 1}")

            # Preallocate file space
            with open(metadata.name, "wb") as f:
                f.truncate(metadata.size)
            print("[DEBUG] Server: Preallocated file space.")

            print("[DEBUG] Server: Starting file transfer...")
            start_time = time.time()

            with open(metadata.name, "r+b") as f:
                while missing_packets:
                    # First, read 4 bytes to get the length of the next packet
                    try:
                        length_data = recv_full(sock, 4)
                    except EOFError:
                        print("[DEBUG] Server: Socket closed, no more data.")
                        break

                    packet_length = struct.unpack("!I", length_data)[0]
                    packet_data = recv_full(sock, packet_length)
                    try:
                        packet = Packet.import_(packet_data)
                        print(f"[DEBUG] Server: Received packet at position {packet.position}")
                        f.seek(packet.position * BUFFER_SIZE)
                        f.write(packet.data)
                        missing_packets.discard(packet.position)
                        print(f"[DEBUG] Server: Updated missing packets: {missing_packets}")
                    except Exception as e:
                        print(f"[ERROR] Server: Error processing packet: {e}")
            elapsed = time.time() - start_time
            print(f"[DEBUG] Server: File downloaded successfully in {elapsed:.2f} seconds. ({(metadata.size/elapsed):.2f} MB/s)")
            sock.close()
        except Exception as e:
            print(f"[ERROR] Server: Exception in receive_file: {e}")
            sock.close()

        if os.path.exists(progress_path):
            if not missing_packets:
                os.remove(progress_path)
            with open(progress_path, "r") as progress:
                progress.writelines(missing_packets)


# ============================
# FILE SENDER (CLIENT)
# ============================

class FileSender:
    """Handles file sending (client-side)"""

    def __init__(self, destination, port):
        self.destination = destination
        self.port = port
        print(f"[DEBUG] FileSender initialized with destination {self.destination}:{self.port}")

    def send_file(self):
        """Handles sending a file to the receiver"""
        try:
            with socket(AF_INET, SOCK_STREAM) as conn:
                conn.connect((self.destination, self.port))
                print("[DEBUG] Client: Connected to peer.")

                file_path = handle_file_path()
                if not os.path.exists(file_path):
                    print("[ERROR] Client: File not found.")
                    return

                metadata = get_metadata_from_file_path(file_path)
                conn.send(metadata.export())
                print(f"[DEBUG] Client: Sent metadata: {metadata}")

                response = conn.recv(1024).decode()
                print(f"[DEBUG] Client: Received response: {response}")

                if response.startswith("ERROR"):
                    print("[ERROR] Client: File already exists on server.")
                    return
                elif response.startswith("MISSING_PACKETS"):
                    missing_packets = list(map(int, response.split(DELIMITER)[1].split(",")))
                    print(f"[DEBUG] Client: Resuming transfer. Missing packets: {missing_packets}")
                else:
                    print("[DEBUG] Client: Sending full file.")
                    missing_packets = list(range(metadata.total_packets))

                with open(file_path, 'rb') as f:
                    for i in missing_packets:
                        f.seek(i * BUFFER_SIZE)
                        data = f.read(BUFFER_SIZE)
                        if not data:
                            print(f"[DEBUG] Client: No data read for packet {i}, breaking.")
                            break
                        packet = Packet(identifier="FILE", position=i, data=data)
                        exported = packet.export()
                        conn.send(exported)
                        print(f"[DEBUG] Client: Sent packet at position {i}, size: {len(exported)} bytes.")
                print("[DEBUG] Client: File transfer complete.")
        except Exception as e:
            print(f"[ERROR] Client: Exception during file send: {e}")


# ============================
# MAIN EXECUTION LOGIC
# ============================

def main():
    """Determines whether to run as sender or receiver"""
    print("[DEBUG] Starting main execution.")
    if DESTINATION_ADDRESS:
        print("[DEBUG] Running in sender mode.")
        sender = FileSender(DESTINATION_ADDRESS, PORT)
        sender.send_file()
    else:
        print("[DEBUG] Running in receiver mode.")
        receiver = FileReceiver(PORT)
        receiver.start_server()


if __name__ == "__main__":
    main()