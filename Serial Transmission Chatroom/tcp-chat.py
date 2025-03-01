import socket
from threading import Thread

# CONFIG
PORT = int(input("Target port: "))
DESTINATION_ADDRESS = input("Target address (xxx.xxx.xxx.xxx, leave empty to wait for connection): ") or None
LOCAL_ADDRESS = ('0.0.0.0', PORT)

# HELPER FUNCTION TO SEND MESSAGES WITH A HEADER
def send_message(sock, msg):
    msg = msg.encode()
    length = len(msg).to_bytes(4, 'big')  # 4-byte header indicating length
    sock.sendall(length + msg)  # Send length + actual message

# RECEIVE FUNCTION
def handle_receive(sock):
    while True:
        try:
            # Read message length first
            length_data = sock.recv(4)
            if not length_data:
                print("[DISCONNECTED]")
                break

            msg_length = int.from_bytes(length_data, 'big')  # Convert bytes to int
            message = sock.recv(msg_length).decode()  # Receive the full message

            print("\n[RECEIVED]:", message, "\n> ", end="")
        except ConnectionResetError:
            print("[Connection closed by peer]")
            break

# INITIALIZE SOCKET
sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

if DESTINATION_ADDRESS:
    # Connecting as a client
    sock.connect((DESTINATION_ADDRESS, PORT))
    print("[CONNECTED TO PEER]")
else:
    # Waiting for incoming connection as server
    sock.bind(LOCAL_ADDRESS)
    sock.listen(1)
    print("[WAITING FOR CONNECTION...]")
    sock, addr = sock.accept()
    print(f"[PEER CONNECTED: {addr}]")

# START RECEIVING THREAD
t1 = Thread(target=handle_receive, args=(sock,), daemon=True)
t1.start()

# SEND MESSAGES
while True:
    msg = input("> ")
    if msg.lower() == "exit":
        break
    send_message(sock, msg)

sock.close()
print("[CONNECTION CLOSED]")