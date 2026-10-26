# Doom Downloader

A decoupled, modular media downloading engine and Windows desktop application for web media and direct files, built with Python, yt-dlp, Requests, and FFmpeg.

Designed with a **strict separation between the Engine (backend)** and the **Frontends (UI)**: the core downloading engine is 100% headless with zero GUI dependencies, allowing it to be used as a standalone Python library, hosted as a REST API server, or driven by external frontends (.NET/Avalonia/WPF, web apps, or CLI tools).

---

## 🏛️ Architecture: Engine vs Frontend

Doom Downloader is split into two independent layers:

```
doom-downloader/
├── core/                  # Standalone Download Engine (Headless, 0 GUI dependencies)
│   ├── engine.py          # Unified DoomEngine facade & entry point
│   ├── downloader.py      # Audio extraction, video stream merging, artwork embedding
│   ├── queue_manager.py   # Thread-safe concurrent download queue & lifecycle
│   ├── direct.py          # Direct HTTP(S) file stream downloader
│   ├── spotify.py         # Zero-credential Spotify metadata & YouTube stream matching
│   ├── url_parser.py      # Universal URL classification & playlist expansion
│   ├── formats.py         # Audio/Video format profiles & resolution presets
│   ├── tagger.py          # Embedded cover art (ID3v2.3) and metadata tagging
│   ├── config.py          # Configuration manager
│   ├── cli.py             # Headless CLI & line-delimited JSON IPC interface
│   └── server.py          # Headless HTTP REST API server (zero extra dependencies)
│
├── gui/                   # Desktop GUI Frontend (CustomTkinter)
│   ├── app.py             # Main application window consuming the engine
│   ├── queue_item_card.py # Interactive download queue cards
│   └── theme.py           # Appearance-aware monochrome palette
│
├── bin/                   # Local FFmpeg & FFprobe binaries
├── tests/                 # Automated test suite (21 unit and integration tests)
├── Launch.bat             # One-click Windows batch launcher
└── main.py                # Multi-mode entry point (GUI, CLI, or Server)
```

---

## ⚙️ Using the Engine Anywhere

Because `core/` has zero dependencies on any GUI library, you can use the downloading engine in any environment:

### 1. As a Python Library (Web servers, bots, scripts)
```python
from core import DoomEngine

engine = DoomEngine(download_dir="./downloads", max_workers=3)

# 1. Resolve URL metadata (YouTube, Spotify, Direct files, etc.)
info = engine.resolve_url("https://open.spotify.com/track/4cOdK2wGLETKBW3PvgPWqT")
print(info["title"], info["artist"])

# 2. Synchronous download with progress callback
path = engine.download(
    url="https://youtube.com/watch?v=...",
    format_label="MP3 (320 kbps)",
    progress_callback=lambda data: print(f"{data['percent']:.1f}%")
)

# 3. Asynchronous queue dispatch
item = engine.enqueue("https://example.com/file.zip", format_label="Original file")
```

### 2. With External Frontends (.NET / Avalonia / WPF / Electron / Bash) via JSON IPC
External frontends in C#/.NET or other languages can drive the engine via standard I/O streams using `--json-progress`:

```powershell
# Inspect URL metadata
python main.py --cli --info "https://..."

# Download with line-delimited JSON progress events streamed to stdout
python main.py --cli --download "https://..." --format "MP3 (320 kbps)" --json-progress

# Query available formats in JSON
python main.py --cli --formats

# Engine health check
python main.py --cli --check
```

Example JSON stream emitted to `stdout`:
```json
{"type": "started", "url": "...", "format": "MP3 (320 kbps)"}
{"type": "progress", "status": "downloading", "percent": 45.2, "speed_str": "3.5 MiB/s", "eta_str": "00:04"}
{"type": "converting", "message": "Embedding album cover art into song file..."}
{"type": "completed", "filepath": "C:\\Downloads\\Song.mp3"}
```

### 3. Hosted on a Server (Lightweight REST API)
Host the engine on any machine or container and connect web frontends (React, Vue, Svelte, or mobile apps) over HTTP:

```powershell
python main.py --server --host 0.0.0.0 --port 8080
```

Available REST Endpoints:
- `GET /api/status` — Health check, FFmpeg availability, queue statistics.
- `GET /api/formats` — List all audio, video, and file format profiles.
- `GET /api/info?url=<URL>&expand=true` — Resolve metadata and playlist tracks.
- `POST /api/download` — Enqueue downloads (`{"url": "...", "format": "...", "download_dir": "..."}`).
- `GET /api/queue` — Real-time queue progress and status.
- `POST /api/queue/pause` & `POST /api/queue/resume` — Queue flow control.
- `POST /api/queue/<id>/cancel` & `POST /api/queue/<id>/retry` — Item control.
- `POST /api/queue/clear` — Clear finished downloads.

### 4. As the Desktop GUI Application
```powershell
python main.py
```
Or double-click `Launch.bat`.

---

## 🎵 Download Options

- **Audio:** MP3 (320 or 192 kbps), M4A, WAV, FLAC, Opus, and OGG Vorbis.
- **Video:** MP4, MKV, and WebM, with best available quality or resolution limits (480p, 720p, 1080p, 1440p, 2160p / 4K).
- **File:** Direct HTTP(S) downloads in their original format, including documents, images, archives, and installers.
- Embedded audio cover art (ID3v2.3) and metadata tagging.
- Single/Bulk input, collection expansion, duplicate skipping, and concurrent downloads.
- Spotify links work in Audio mode: track and playlist metadata are extracted and matched to YouTube audio streams without Spotify API credentials.
- Collapsible file browser library panel with folder navigation and search.
- Light/dark appearance and saved preferences.

---

## 🛠️ Controls (Desktop UI)

Choose Audio, Video, or File mode at the top. Paste a link or collection, select the format and destination folder, and click Download.

- `Enter`: Download in Single mode.
- `Shift+Enter` or `Ctrl+Shift+Enter`: Add line and switch to Bulk mode.
- `Ctrl+Enter`: Download in either Single or Bulk mode.
- Pasting multiple lines automatically switches to Bulk mode.
- Files button: Opens the side library panel.
- Collections checkbox: Expands supported playlists or multi-item collections.

---

## 📦 Installation & Setup

Requires Python 3.11+ and FFmpeg/FFprobe.

```powershell
git clone https://github.com/arunmauryaz/doom-downloader.git
cd doom-downloader
```

Install FFmpeg on system PATH or place `ffmpeg.exe` and `ffprobe.exe` in `bin/`.

Install dependencies:
```powershell
python -m pip install -r requirements.txt
```

Launch the app:
```powershell
python main.py
```

---

## 🧪 Automated Testing

Run the test suite across the engine, CLI, REST server, formats, and UI:

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

All 21 test suites cover:
- Standalone engine facade, resolution, and format discovery
- Line-delimited CLI JSON IPC protocols
- Headless HTTP REST server endpoints
- Format profiles and resolution capping
- Direct file streaming, atomic writes, and duplicate handling
- Cancellation and cleanup
- Embedded media extraction with FFmpeg
- Interface behaviors and widget states

---

## 📄 License

[MIT](LICENSE). Third-party dependencies retain their own licenses.
