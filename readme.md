# Project Repository Overview

This repository contains multiple projects that demonstrate skills in **networking, file synchronization, serial communication, and persistence storage**. Below is a breakdown of each project, what it does, and the technologies used.

---

## 1. Basic HTTP Server
**Files:** `server.py`, `url.json`

**Summary:** This project implements a simple HTTP server that supports URL redirection. Users can shorten URLs and retrieve them via stored short codes.

**Features:**
- Redirects users based on stored URLs.
- Supports `?name=` query parameters for custom short links.
- Uses JSON (`url.json`) for persistent storage.

**Technologies Used:**
- Python (`http.server`, `socketserver`, JSON handling, threading).

**What I Learned:**
- Working with HTTP requests and responses.
- Handling JSON-based data persistence.
- Implementing query string parameters for user-defined URL keys.

---

## 2. File Synchronization Tool (fsync)
**Files:** `fsync` (Not uploaded, assumed to be planned)

**Summary:** This tool monitors a directory for changes and automatically syncs updated files to another directory or remote server.

**Planned Features:**
- Detect file changes (creation, modification, deletion).
- Sync files locally or over a network (future work).
- Use checksums for efficient transfers.

**Technologies Used:**
- Python (`watchdog`, `shutil`, threading for real-time monitoring).

**What I Expect to Learn:**
- Event-driven programming (watching files in real-time).
- Efficient file transfer techniques.
- Implementing networking for remote synchronization.

---

## 3. Persistent Dictionary
**Files:** `persistent-dict.py`, `data.json`

**Summary:** A CLI-based dictionary that allows users to store key-value pairs persistently across sessions.

**Features:**
- Load existing dictionary data from `data.json`.
- Allow users to add, retrieve, and modify stored values.
- Saves changes automatically for persistence.

**Technologies Used:**
- Python (`json`, CLI interaction, file handling).

**What I Learned:**
- Handling file-based persistence.
- Creating interactive CLI applications.
- Improving user experience with input validation.

---

## 4. Serial Transmission Chatroom
**Files:** `serial.py`, `tcp-chat.py`

**Summary:** Implements two communication methods for chat applications: one using **serial communication** and another using **TCP sockets**.

**Features:**
- `serial.py`: Uses serial communication to send messages between devices.
- `tcp-chat.py`: Uses TCP sockets to allow multiple clients to chat over a network.

**Technologies Used:**
- Python (`socket`, `serial`, `threading`).

**What I Learned:**
- Basics of serial communication.
- Implementing network communication using TCP sockets.
- Handling concurrent connections with threads.