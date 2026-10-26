# Doom Downloader v1.1.0

A modular, high-performance media downloading engine and Windows desktop application for web media and direct files.

## What's New in v1.1.0

- **Decoupled Backend Engine (`core/`)**:
  - The core engine now has **zero GUI dependencies** and can be used as a standalone Python library (`from core import DoomEngine`).
  - Supports embedding into web backends (FastAPI/Flask/Django), scripts, and automated bots.
- **Headless CLI & JSON IPC (`--cli`)**:
  - Enables external frontends (**C# / .NET / Avalonia / WPF**, Electron, Bash) to control the engine over standard I/O streams using `--json-progress`.
  - Supports `--info <URL>`, `--download <URL>`, `--formats`, and `--check`.
- **Headless HTTP REST API Server (`--server`)**:
  - Built-in lightweight REST API server using standard library `ThreadingHTTPServer` (no extra dependencies).
  - Provides `/api/status`, `/api/formats`, `/api/info`, `/api/download`, and `/api/queue` endpoints with full CORS support.
- **Multi-Mode Entrypoint (`main.py`)**:
  - Automatically routes to Desktop GUI (default), Headless CLI (`--cli`), or REST Server (`--server`).
- **Comprehensive Automated Test Suite**:
  - 21 automated unit and integration tests passing across engine, CLI, server, formats, and UI.

## Install & Run

1. Download and extract `doom-downloader-1.1.0-source.zip`.
2. Install Python 3.11 or newer.
3. Install FFmpeg and FFprobe on PATH or place executables in `bin/`.
4. Double-click `Launch.bat` to launch the Desktop GUI, or run:
   - `python main.py` for Desktop GUI
   - `python main.py --cli --help` for Headless CLI
   - `python main.py --server` for REST API Server

`SHA256SUMS.txt` contains the archive checksum.
