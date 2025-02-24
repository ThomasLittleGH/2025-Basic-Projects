import json
import http.server
import socketserver
from http import HTTPStatus
import threading
import os
import random
import string
import urllib.parse

DATA_FILE = "url.json"

# Ensure the data file exists
if not os.path.exists(DATA_FILE):
    with open(DATA_FILE, 'w') as f:
        json.dump({}, f)

# Load existing data
with open(DATA_FILE, 'r') as f:
    try:
        data = json.load(f)
    except json.JSONDecodeError:
        data = {}  # Handle case where file is empty or corrupted


def save_data():
    """Save dictionary data to file."""
    with open(DATA_FILE, 'w') as f:
        json.dump(data, f, indent=4)


def generate_random_string(length=6):
    """Generate a short, random alphanumeric string."""
    characters = string.ascii_letters + string.digits  # A-Z, a-z, 0-9
    return ''.join(random.choices(characters, k=length))


def is_valid_url(url):
    """Check if the URL is valid."""
    parsed = urllib.parse.urlparse(url)
    return parsed.scheme in {"http", "https"} and parsed.netloc


""" HANDLER """


class Handler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        print("Visited path:", self.path)
        path = self.path[1:]  # Remove leading '/'

        if self.path == '/':
            self.send_json_response({"message": "Hello, world!"})
            return

        if path in data:
            # Redirect to stored URL
            self.send_response(HTTPStatus.FOUND)  # 302 Temporary Redirect
            self.send_header("Location", data[path])
            self.end_headers()
            return

        # Handle a new URL submission
        decoded_path = urllib.parse.unquote(path)  # Decode URL-encoded input

        if not is_valid_url(decoded_path):
            decoded_path = "https://" + decoded_path

        if not is_valid_url(decoded_path):
            self.send_json_response({"error": "Invalid URL"}, status=HTTPStatus.BAD_REQUEST)
            return

        # Check if the URL is already stored
        for key, stored_url in data.items():
            if stored_url == decoded_path:
                self.send_json_response({"short_url": f"http://localhost:8000/{key}"})
                return

        # Generate a new short URL
        seed = generate_random_string()
        data[seed] = decoded_path
        save_data()

        self.send_json_response({"short_url": f"http://localhost:8000/{seed}"})

    def send_json_response(self, data, status=HTTPStatus.OK):
        """Send a JSON response."""
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(data).encode())


""" SOCKET ADDRESS """

PORT = 8000


# Use ThreadingTCPServer instead of TCPServer
class ThreadingHTTPServer(socketserver.ThreadingMixIn, socketserver.TCPServer):
    pass


sk = ThreadingHTTPServer(("0.0.0.0", PORT), Handler)
print(f"Server starting at http://localhost:{PORT}")

t1 = threading.Thread(target=sk.serve_forever, daemon=True)
t1.start()

input("Press ENTER to close...\n")
sk.server_close()