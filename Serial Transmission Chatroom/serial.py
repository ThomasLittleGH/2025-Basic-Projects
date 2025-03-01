import socket
import struct
import threading
import zlib

# ============================
# CONFIGURATION
# ============================

SHOW_LOGS = bool(input("Display logs in console? (1/0): "))
DESTINATION_ADDRESS = input("Target address (xxx.xxx.xxx.xxx), or leave empty to listen: ") or None
SOURCE_ID = 1
DESTINATION_ID = 2

if not DESTINATION_ADDRESS:
    print("[WAITING FOR CONNECTION]")
    SOURCE_ID = 2
    DESTINATION_ID = 1

seq = 0

# ============================
# PACKET CLASS
# ============================

class Packet:
    def __init__(self, *args):
        if len(args) == 4:
            # Called as Packet(s_id, d_id, seq, msg) → Sender
            s_id, d_id, seq, msg = args
            self.s_id = s_id
            self.d_id = d_id
            self.seq = seq
            self.msg_len = len(msg)

            # Ensure msg is in byte format
            if isinstance(msg, str):
                msg = msg.encode()

            self.msg = msg
            self.checksum = self.calculate_checksum()

        else:
            # Called as Packet(packet) → Receiver
            packet = args[0]
            header = packet[:8]
            payload = packet[8:9]  # Only 1 byte for the message

            self.s_id, self.d_id, self.seq, self.msg_len, self.checksum = struct.unpack("!HHHBB", header)
            self.msg = payload

    def calculate_checksum(self):
        return zlib.crc32(self.msg) & 0xFF  # CRC-8

    def get_header(self):
        return struct.pack("!HHHBB", self.s_id, self.d_id, self.seq, self.msg_len, self.checksum)

    def send_to(self, addr):
        s = socket.socket(socket.AF_INET, socket.SOCK_RAW, socket.IPPROTO_UDP)  # Use UDP for better compatibility
        packet = self.get_header() + self.msg
        print("packet: ", packet)
        s.sendto(packet, (addr, 0))

    def is_valid(self):
        """Validate checksum"""
        return self.checksum == (zlib.crc32(self.msg) & 0xFF)

    def __str__(self):
        return f"[Packet] From {self.s_id} → {self.d_id}, Seq {self.seq}, Msg {self.msg.decode() if self.is_valid() else '[CORRUPTED]'}"

# ============================
# RECEIVER FUNCTION
# ============================

def receiver():
    print("[DEBUG] Receiver started")
    s_receive = socket.socket(socket.AF_INET, socket.SOCK_RAW, socket.IPPROTO_UDP)

    while True:
        packet, addr = s_receive.recvfrom(1024)

        # Process incoming packet
        processed_packet = Packet(packet)

        # Ignore packets not meant for us
        if processed_packet.d_id != SOURCE_ID:
            continue

        if SHOW_LOGS:
            print(processed_packet)

        if processed_packet.is_valid():
            print(f"[RECEIVED] {processed_packet.msg.decode()} from {processed_packet.s_id}")
        else:
            print("[ERROR] Packet corrupted!")

# ============================
# START RECEIVER THREAD
# ============================

receiver_thread = threading.Thread(target=receiver, daemon=True)
receiver_thread.start()

# ============================
# MAIN SENDING LOOP
# ============================

while True:
    message = input("> ")

    # SEND THE START MESSAGE
    p = Packet(SOURCE_ID, DESTINATION_ID, seq, b'\x02')  # Use STX (Start of Text)
    p.send_to(DESTINATION_ADDRESS)
    seq += 1

    # SEND MESSAGE BYTE BY BYTE
    for c in message:
        p = Packet(SOURCE_ID, DESTINATION_ID, seq, c)
        print(p)
        p.send_to(DESTINATION_ADDRESS)
        seq += 1

    # SEND THE END MESSAGE
    p = Packet(SOURCE_ID, DESTINATION_ID, seq, b'\x03')  # Use ETX (End of Text)
    p.send_to(DESTINATION_ADDRESS)
    seq += 1