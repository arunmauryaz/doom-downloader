# Doom Downloader v1.2.0

A universal, high-performance media downloading engine and Windows desktop application for web media and direct files.

## What's New in v1.2.0

- **⚡ IDM-Style Multi-Segmented Packet Downloader**:
  - Direct HTTP(S) files are partitioned into parallel HTTP Range slices (`Range: bytes=start-end`) using up to 8–16 simultaneous connections.
  - Saturated line bandwidth speeds with non-colliding parallel file writing.
  - State tracking in `.doomstate` and `.doompart` preserving exact byte progress.
- **🚀 Turbo Stream Acceleration**:
  - 8 concurrent fragment downloads (`concurrent_fragment_downloads: 8`) for HLS (`.m3u8`) and DASH (`.mpd`) video streams.
  - Large TCP socket buffer reads (128 KB buffer, 10 MB chunks) and automatic retries.
- **⏸️ True Pause, Resume, and Redo**:
  - Full pause and resume capability across both desktop GUI and headless queue engine.
  - Resumes interrupted downloads right from current byte offsets without restarting from 0%.
  - Three-dots context menu (⋮) with Pause, Resume, Redo from Start, and Cancel.
- **🌐 Universal Platform Media Scraper**:
  - **Steam Store**: Scrapes Steam game trailers in 1080p/4K HLS/DASH/MP4 directly from store pages (`store.steampowered.com/app/...`).
  - **Social Platforms**: Dedicated detection for Twitter / X, Instagram Reels, Facebook, TikTok, Reddit, and Twitch.
  - **Universal Fallback Scraper**: HTML5 `<video>`, `<source>`, OpenGraph tags, and in-script `.m3u8`/`.mp4` stream resolution.
- **💻 Fast Short-Lived CLI**:
  - Quick positional syntax: `python main.py download <url> [quality] [path]` or `python main.py <url>`.
  - Format alias shortcuts (`best`, `4k`, `1080p`, `720p`, `mp3`, `320k`, `wav`, `flac`, `original`).
  - Sleek ASCII progress bar with real-time transfer speed and ETA.
  - Headless Linux / Docker / SSH detection preventing Tkinter display crashes.
- **✨ Universal Link Input & UX**:
  - Removed rigid upfront mode selection tabs (`Audio`, `Video`, `File`). Replaced with a single URL bar and smart live detection banner.
  - Context-adaptive format dropdown showing video resolutions alongside audio extraction options (`[Audio] MP3`, `[Audio] WAV`).
- **🛡️ Duplicate Prevention**:
  - Pre-download duplicate check in destination folder to skip redundant downloads unless `--overwrite` is specified.
- **🧪 Automated Test Suite**:
  - Expanded test suite to **28 automated unit and integration tests** passing with 100% success rate.
- **📚 Developer Specification**:
  - Created `docs/UNIVERSAL_DOWNLOADER_SPEC.md` detailing architecture, internal protocols, and the universal downloader roadmap.

## Install & Run

1. Clone or extract the repository.
2. Install Python 3.11 or newer.
3. Install FFmpeg and FFprobe on PATH or place executables in `bin/`.
4. Double-click `Launch.bat` to launch the Desktop GUI, or run:
   - `python main.py` for Desktop GUI
   - `python main.py download <url>` for Fast CLI
   - `python main.py --server` for REST API Server
