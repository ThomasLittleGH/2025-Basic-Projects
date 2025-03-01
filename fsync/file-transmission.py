import shlex
from socket import socket, SOCK_STREAM, AF_INET
import os

# ============================
# CONFIGURATION
# ============================
PORT = 8000
DESTINATION_ADDRESS = input("Target address (xxx.xxx.xxx.xxx, leave empty to wait for connection): ") or None
LOCAL_ADDRESS = ('0.0.0.0', PORT)
BUFFER_SIZE = 8192  # Size of data chunks for transfer

# ============================
# SERVER MODE (RECEIVER)
# ============================
if not DESTINATION_ADDRESS:
    print("[WAITING FOR CONNECTION...]")
    with socket(AF_INET, SOCK_STREAM) as server_socket:
        server_socket.bind(LOCAL_ADDRESS)
        server_socket.listen(1)
        sock, addr = server_socket.accept()
        print(f"[PEER CONNECTED: {addr}]")

        # Receive filename
        file_name = sock.recv(1024).decode()
        print(f"RECEIVED FILE NAME {file_name}.")
        if os.path.exists(file_name):
            print("[ERROR: FILE ALREADY EXISTS]")
            sock.send(b"ERROR: File already exists")
            sock.close()
        else:
            print("[FILE TRANSFER INITIATED]")

            # Receive file
            with open(file_name, 'wb') as f:
                while True:
                    packet = sock.recv(BUFFER_SIZE)
                    if not packet:  # Empty packet means end of file
                        break
                    f.write(packet)
            print("[FILE DOWNLOADED SUCCESSFULLY]")

        sock.close()

# ============================
# CLIENT MODE (SENDER)
# ============================
else:
    with socket(AF_INET, SOCK_STREAM) as conn:
        conn.connect((DESTINATION_ADDRESS, PORT))
        print("[CONNECTED TO PEER]")

        file_path = input("Enter full file path: ").strip()
        file_path = shlex.split(file_path)[0]  # Automatically removes escape sequences
        file_path = os.path.expanduser(file_path)  # Expands ~ to full path
        file_path = os.path.normpath(file_path)  # Normalizes slashes

        print(f"[DEBUG] File Path: {file_path}")  # Print the resolved path

        if not os.path.exists(file_path):
            print("[ERROR: FILE NOT FOUND]")
        else:
            file_name = os.path.basename(file_path)
            conn.send(file_name.encode())  # Send filename first

            # Send file data
            with open(file_path, 'rb') as f:
                print(f"[FILE FOUND: SENDING {file_name}]")
                while True:
                    packet = f.read(BUFFER_SIZE)
                    if not packet:
                        break
                    conn.send(packet)

            print("[FILE TRANSFER COMPLETE]")

print("Thanks for using this software :)")