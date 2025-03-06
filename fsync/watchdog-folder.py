import time
import shlex
from typing import List, Tuple, Dict, Any, Union
from math import ceil
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import os
import datetime
import hashlib
import json
import struct
from socket import socket, SOCK_STREAM, AF_INET
from zlib import compress, decompress


# ============================
# CONFIGURATION & CONSTANTS
# ============================
#TODO: fix the file transmission so it works, no lo he adaptado de como estaba antes xd
#TODO: Change it so folders don't create sub dictionaries in the main dictionary, but rather get added to the main one.

BUFFER_SIZE = 1024 ** 2 * 4
PATH = os.getcwd()  # directory to watch (here, current directory)
DATA_FILE = PATH + "/data.json"
DELIMITER = "#%E&T"
PORT = 8000
DESTINATION_ADDRESS = None #input("Target address (xxx.xxx.xxx.xxx, leave empty to wait for connection): ") or None
LOCAL_ADDRESS = ('0.0.0.0', PORT)
cur_data = dict()

print(f"[DEBUG] PATH: {PATH}")
print(f"[DEBUG] PORT: {PORT}")
print(f"[DEBUG] DESTINATION_ADDRESS: {DESTINATION_ADDRESS}")
print(f"[DEBUG] LOCAL_ADDRESS: {LOCAL_ADDRESS}")
print(f"[DEBUG] BUFFER_SIZE: {BUFFER_SIZE}")
print(f"[DEBUG] DELIMITER: {DELIMITER}")


# TODO: Integrate renaming
class DataManager:

    def __init__(self, file):
        self.DATA_FILE = file

    def load_data(self, ) -> (bool, dict):
        """
        Load data from the JSON file.

        This function ensures that the file exists, checks for read permissions,
        and attempts to load the JSON data. It returns a tuple where the first element
        indicates success (True/False), and the second element is the loaded dictionary
        (or an empty dict on failure).

        Returns:
            (bool, dict): A tuple containing a success flag and the loaded data.
        """
        # If the file does not exist, try to create it with an empty dict.
        if not os.path.exists(self.DATA_FILE):
            print(f"[DEBUG] {self.DATA_FILE} does not exist. Attempting to create a new file.")
            try:
                with open(self.DATA_FILE, 'w') as f:
                    json.dump({}, f)
            except PermissionError:
                print(f"[DEBUG] Permission denied while creating {self.DATA_FILE}.")
                return (False, {})
            except Exception as e:
                print(f"[DEBUG] Unexpected error while creating file: {e}")
                return (False, {})

        # Check if the file is readable.
        if not os.access(self.DATA_FILE, os.R_OK):
            print(f"[DEBUG] No read permission for {self.DATA_FILE}.")
            return (False, {})

        # Attempt to load the data.
        try:
            with open(self.DATA_FILE, 'r') as f:
                data = json.load(f)
            print("[DEBUG] Data loaded successfully.")
            return (True, data)
        except json.JSONDecodeError:
            print("[DEBUG] JSON decoding error. File might be empty or corrupted. Returning empty data.")
            return (False, {})
        except PermissionError:
            print("[DEBUG] Permission denied while reading data from file.")
            return (False, {})
        except Exception as e:
            print(f"[DEBUG] Unexpected error while loading data: {e}")
            return (False, {})

    def save_data(self, data: dict) -> bool:
        """
        Save dictionary data to the JSON file.

        This function checks for write permissions (if the file exists) and then attempts
        to write the provided data to the file.

        Args:
            data (dict): The data dictionary to be saved.

        Returns:
            bool: True if the data was saved successfully, False otherwise.
        """
        # If the file exists, check for write permissions.
        if os.path.exists(self.DATA_FILE) and not os.access(self.DATA_FILE, os.W_OK):
            print(f"[DEBUG] No write permission for {self.DATA_FILE}.")
            return False

        try:
            with open(self.DATA_FILE, 'w') as f:
                json.dump(data, f, indent=4)
            print("[DEBUG] Data saved successfully.")
            return True
        except PermissionError:
            print("[DEBUG] Permission denied while writing to file.")
            return False
        except Exception as e:
            print(f"[DEBUG] Unexpected error while saving data: {e}")
            return False


# Export and import to dict()
class FileClass:
    def __init__(self, name: str, size, ctime, mtime):
        self.name = name
        self.size = size
        self.ctime = ctime
        self.mtime = mtime

    def __str__(self):
        return (
            self.name
            + " - "
            + str(round(self.size / 1024**2, 2))
            + " MB (created at "
            + str(datetime.datetime.fromtimestamp(self.ctime))
            + ", last modification: "
            + str(datetime.datetime.fromtimestamp(self.mtime))
            + ")"
        )

    def to_dict(self):
        """Exports the FileClass instance to a dictionary."""
        return {
            "name": self.name,
            "size": self.size,
            "ctime": self.ctime,
            "mtime": self.mtime,
        }

    @classmethod
    def from_dict(cls, data: dict):
        """Creates a FileClass instance from a dictionary."""
        return cls(
            name=data.get("name"),
            size=data.get("size"),
            ctime=data.get("ctime"),
            mtime=data.get("mtime"),
        )


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
            print(f"[DEBUG] Server: File downloaded successfully in {elapsed:.2f} seconds. ({(metadata.size/(elapsed * 1024**2)):.2f} MB/s)")
            sock.close()
        except Exception as e:
            print(f"[ERROR] Server: Exception in receive_file: {e}")
            sock.close()
        finally:
            # Update progress file with any missing packets before closing
            try:
                if not missing_packets:
                    os.remove(progress_path)
                else:
                    with open(progress_path, "w") as progress:
                        for pkt in sorted(missing_packets):
                            progress.write(f"{pkt}\n")
                print(f"[DEBUG] Server: Progress file updated with missing packets: {missing_packets}")
            except Exception as e:
                print(f"[ERROR] Server: Could not update progress file: {e}")
            sock.close()


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

                file_path = sanitize_file_path()
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


"""
DATA STRUCTURE:
data = {
    file 1 : [
        metadata : [],
        packet_1_hash,
        packet_2_hash
    ],
    
    file 2 : [
        metadata : [],
        packet_1_hash,
        packet_2_hash,
        packet_3_hash
    ]
}
For 100GB of data split into 4MB packets:
	•	JSON File Size: Approximately 1–2MB (mostly storing MD5 hashes).
	•	RAM Impact: Minimal, as a few megabytes is trivial for modern computers.
	•	Load/Save Times: Likely in the range of tens of milliseconds, making it very efficient for your use case.
"""


# TODO Make it so that changes made in folders get added to the main created lists instead of folder ones
# BENCHMARK : 44s for 13Gb, 2s for 700MB


def detect_offline_changes(data_manager: "DataManager") -> None:
    start: float = time.time()
    new_data_tuple: Tuple[bool, Dict[str, Any]] = data_manager.load_data()
    new_data: Dict[str, Any] = new_data_tuple[1] if new_data_tuple[0] else {}
    old_data: Dict[str, Any] = build_local_data_file(PATH)
    global cur_data
    cur_data = old_data

    elapsed: float = time.time() - start
    print("TOOK:", elapsed, "seconds")
    print_directory(cur_data, recursive=True)
    print_directory(new_data, recursive=True)

    def compare_dicts(old: Dict[str, Any], new: Dict[str, Any]) -> Dict[str, Any]:
        deleted: List[Tuple[str, Any]] = []
        modified: List[Tuple[str, Any]] = []
        renamed: List[Tuple[str, Any]] = []
        created: List[Tuple[str, Any]] = []

        # Check for deletions and modifications
        for key in old:
            if key not in new:
                deleted.append((key, old[key]))
            else:
                """# If the value is a dictionary, compare recursively
                if isinstance(old[key], dict) and isinstance(new[key], dict):
                    sub_diff: Dict[str, Any] = compare_dicts(old[key], new[key])
                    if sub_diff:
                        # TODO : fix to intented function.
                        deleted += sub_diff["deleted"]
                        created += sub_diff["created"]
                        modified += sub_diff["modified"]
                        renamed += sub_diff["renamed"]
                else:
                    # For files, compare metadata and/or hash lists"""
                if old[key] != new[key]:
                    modified.append((key, new[key]))

        # Check for additions
        for key in new:
            if key not in old:
                created.append((key, new[key]))

        # Check for renames
        # We assume that for files the value is a list where index 1 holds the hash list.
        created_hashes: List[List[str]] = [entry[1][1] for entry in created if isinstance(entry[1], list) and len(entry[1]) > 1]
        renamed_candidates: List[Tuple[str, Any]] = [
            file for file in deleted
            if isinstance(file[1], list) and len(file[1]) > 1 and file[1][1] in created_hashes
        ]
        renamed.extend(renamed_candidates)

        # Remove renamed items from deleted and created
        deleted = [file for file in deleted
                   if not (isinstance(file[1], list) and len(file[1]) > 1 and file[1][1] in [r[1][1] for r in renamed])]
        created = [file for file in created
                   if not (isinstance(file[1], list) and len(file[1]) > 1 and file[1][1] in [r[1][1] for r in renamed])]

        differences: Dict[str, Any] = {
            "deleted": deleted,
            "modified": modified,
            "renamed": renamed,
            "created": created
        }

        return differences

    difference: Dict[str, Any] = compare_dicts(old_data, new_data)
    #print_differences(difference)


def build_local_data_file(path: str) -> Dict[str, Any]:
    data: Dict[str, Any] = {}
    entries = os.scandir(path)  # list all files/folders in current directory
    for file in entries:
        if file.is_dir():
            aux = build_local_data_file(file.path)
            for key in aux:
                data[key] = aux[key]
        elif not file.name.startswith(".") and not file.name == "data.json":
            data[file.path] = [metadata_recovery(file), individually_compute_md5(file.path)]
    return data


def metadata_recovery(file: os.DirEntry) -> Dict[str, Union[str, int, float]]:
    return {
        "name": file.name,
        "size": file.stat().st_size,
        "ctime": file.stat().st_ctime,
        "mtime": file.stat().st_mtime,
    }


def individually_compute_md5(file_path: str) -> List[str]:
    output: List[str] = []
    with open(file_path, 'rb') as f:
        # Read the file in chunks of 4MB
        for chunk in iter(lambda: f.read(BUFFER_SIZE), b''):
            output.append(hashlib.md5(chunk).hexdigest())
    return output


def compute_md5(file_path: str) -> str:
    md5_obj = hashlib.md5()
    with open(file_path, 'rb') as f:
        # Read the file in chunks of 4MB
        for chunk in iter(lambda: f.read(BUFFER_SIZE), b''):
            md5_obj.update(chunk)
    return md5_obj.hexdigest()


def print_directory(data: Dict[str, Any], recursive: bool = False, prefix: str = "|– ") -> None:
    print("-" * 32)
    print("WORKING DIRECTORY".center(32))
    print("-" * 32)

    def recursive_print_directory(data: Dict[str, Any], recursive: bool, prefix: str) -> None:
        for entry in data:
            aux = data[entry]
            if isinstance(aux, list):
                # Assuming aux[0] is a metadata dictionary for a file.
                file_obj = FileClass.from_dict(aux[0])
                print(prefix + str(file_obj))
            elif recursive:
                print(os.path.basename(entry) + "/")
                recursive_print_directory(aux, recursive=recursive, prefix="    " + prefix)

    recursive_print_directory(data, recursive=recursive, prefix=prefix)


def print_differences(data: Dict[str, Any]) -> None:
    print("-" * 32)
    print("DIFFERENCES".center(32))
    print("-" * 32)


    if not data:
        return
    print("CREATED (" + str(len(data['created'])) + '):')
    for file in data['created']:
        print("|-", str(FileClass.from_dict(file[1][0])))
    print("RENAMED (" + str(len(data['renamed'])) + '):')
    for file in data['renamed']:
        print("|-", str(FileClass.from_dict(file[1][0])))
    print("MODIFIED (" + str(len(data['modified'])) + '):')
    for file in data['modified']:
        print("|-", str(FileClass.from_dict(file[1][0])))
    print("DELETED (" + str(len(data['deleted'])) + '):')
    for file in data['deleted']:
        print("|-", str(FileClass.from_dict(file[1][0])))
    print("end")


def sanitize_file_path(fp:str) -> str:
    fp = shlex.split(fp)[0]
    fp = os.path.expanduser(fp)
    fp = os.path.normpath(fp)
    print(f"[DEBUG] Resolved File Path: {fp}")
    return fp


def get_metadata_from_file_path(fp:str) -> Metadata:
    """Extracts metadata from a file path"""
    file_name = os.path.basename(fp)
    file_size = os.path.getsize(fp)
    md = Metadata(name=file_name, size=file_size)
    print(f"[DEBUG] Generated Metadata: {md}")
    return md


def send_packet(position:int, data:bytes) -> Packet:
    """Creates and returns a packet for given position and data"""
    packet = Packet(identifier="FILE", position=position, data=data)
    print(f"[DEBUG] Prepared packet for position {position}")
    return packet


def recv_full(sock:socket, n:int):
    """Receive exactly n bytes from the socket."""
    data = b""
    while len(data) < n:
        more = sock.recv(n - len(data))
        if not more:
            raise EOFError("Socket closed before we received enough data")
        data += more
    return data


class MyHandler(FileSystemEventHandler):
    # TODO: save file to dictionary
    def on_created(self, event):
        if not event.is_directory and not event.src_path.endswith('~'):
            print(f"File created: {event.src_path}")

    def on_modified(self, event):
        if not event.is_directory and not event.src_path.endswith('~'):
            print(f"File modified: {event.src_path}")
            print("Current path", PATH)
            new_path = '/'.join(event.src_path.split("/")[:-1])
            print("Path to file modified", new_path)
            sub_dir = new_path.replace(PATH, "")
            print("subdirectory:", sub_dir)
            progress = PATH[:]
            aux_data = cur_data
            for step in sub_dir.split("/"):
                print("step:", step)
                progress += "/"+step
                if progress is aux_data:
                    print("Found my step")
                else:
                    print("Creating a new step")
                    aux_data[progress] = dict()
                aux_data = aux_data[progress]
                    # Todo : Ill have to find a way to save it to main branch






            # TODO : search for the file in dictionary and update it

    def on_deleted(self, event):
        if not event.is_directory and not event.src_path.endswith('~'):
            print(f"File deleted: {event.src_path}")


# Initialize and start observer
data_manager = DataManager(DATA_FILE)
detect_offline_changes(data_manager)

observer = Observer()
observer.schedule(MyHandler(), path=PATH, recursive=True)
observer.start()

print(f"Watching changes in {PATH}...")
print(cur_data)
try:
    while True:
        time.sleep(1)  # keep the script running
except KeyboardInterrupt:
    observer.stop()
observer.join()
