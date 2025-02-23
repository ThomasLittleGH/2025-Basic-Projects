import json
import os

DATA_FILE = "Persistent Dictionary/data.json"

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

while True:
    print("\nPersistent dictionary")
    print("Insert 'log' to view records | 'q' to exit")
    key = input("Enter a key: ").strip()

    if key == 'q':
        save_data()
        break
    if key == 'log':
        print(json.dumps(data, indent=4))  # Pretty-print dictionary
        continue

    if key in data:
        print(f"Current Value: {data[key]}")
        modify = input("Do you want to change the value? (s/n): ").strip().lower()
        if modify != "s":
            continue

    value = input("Enter a value: ").strip()
    data[key] = value
    save_data()  # Save immediately after modification
    print(f"Key '{key}' updated successfully.")