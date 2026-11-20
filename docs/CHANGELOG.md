# Changelog

## 1.2.0 — 2026-10-26

IDM-style packet acceleration, universal platform support, fast CLI, and pause/resume engine.

- **IDM-Style Multi-Segmented Packet Downloader**:
  - Direct HTTP(S) files are partitioned into parallel HTTP Range slices (`Range: bytes=start-end`) using up to 8–16 simultaneous socket connections for maximum bandwidth saturation.
  - Multi-threaded non-colliding writes with zero merge delay at completion.
  - State tracking in `.doomstate` and `.doompart` preserving exact byte progress.
- **Turbo Stream Acceleration**:
  - Configured 8 concurrent fragment downloads (`concurrent_fragment_downloads = 8`) for HLS (`.m3u8`) and DASH (`.mpd`) video/audio streams.
  - Buffered TCP reads (128 KB buffer, 10 MB chunks) and automatic fragment retries.
- **True Pause, Resume, and Redo**:
  - Interactive pause and resume in desktop GUI cards and queue manager.
  - Resumes interrupted or paused downloads from partial byte offsets without redownloading from scratch.
  - Three-dots context menu with Pause, Resume, Redo from Start, and Cancel.
- **Universal Multi-Platform Media Scraper**:
  - **Steam Store**: Scrapes Steam game trailers in 1080p/4K HLS/DASH/MP4 directly from store pages (`store.steampowered.com/app/...`).
  - **Social Media**: Native detection and extraction for Twitter / X (`x.com`), Instagram Reels (`instagram.com`), Facebook Videos (`facebook.com`, `fb.watch`), TikTok (`tiktok.com`), Reddit (`reddit.com`), and Twitch (`twitch.tv`).
  - **Arbitrary Websites**: Universal fallback scraper extracting HTML5 `<video>`, `<source>`, OpenGraph tags, and in-script `.m3u8`/`.mp4` streams.
- **Fast Short-Lived CLI**:
  - Intuitive commands: `python main.py download <url> [quality] [path]`, `python main.py <url>`, `python main.py info <url>`, `formats`, and `check`.
  - Smart format alias normalizer: `best`, `4k`, `1080p`, `720p`, `mp3`, `320k`, `wav`, `flac`, `original`.
  - Real-time ASCII progress bar with ETA and file size reporting.
  - Headless Linux / Docker / SSH detection preventing Tkinter display crashes.
- **Universal Link Input (UI/UX)**:
  - Removed rigid upfront mode selection tabs (`Audio`, `Video`, `File`). Replaced with a single URL bar and smart live detection banner.
  - Context-adaptive format dropdown showing video resolutions alongside audio extraction options (`[Audio] MP3`, `[Audio] WAV`).
- **Duplicate Prevention**:
  - Pre-download duplicate detection checking destination directory to skip redundant downloads unless `--overwrite` is specified.
- **Automated Test Suite**:
  - Expanded test suite to 28 automated unit and integration tests with 100% pass rate.
- **Documentation**:
  - Added comprehensive `docs/UNIVERSAL_DOWNLOADER_SPEC.md` for contributors and autonomous agents.

## 1.1.0 — 2026-10-26

Decoupled core download engine from UI frontends.

- Standalone `DoomEngine` backend facade with zero GUI dependencies.
- Headless CLI & line-delimited JSON IPC interface (`--cli`, `--json-progress`) for .NET, Avalonia, WPF, and external processes.
- Headless HTTP REST API server (`--server`) with full queue management and CORS support.
- Multi-mode entry point in `main.py` routing to GUI, CLI, or Server modes.
- Expanded automated test suite with 21 unit and integration tests covering engine, CLI, and REST API.
- Updated documentation with external frontend integration examples.

## 1.0.0 — 2026-10-25

Initial public release.

- Audio extraction to MP3, M4A, WAV, FLAC, Opus, and OGG.
- MP4, MKV, and WebM video downloads with resolution presets.
- Website media discovery using yt-dlp and direct HTTP(S) file downloads.
- Spotify metadata matching to YouTube audio.
- Single and Bulk input with automatic detection and keyboard shortcuts.
- Concurrent queue, cancellation, retries, filters, and duplicate checks.
- Embedded artwork and metadata controls.
- Collapsible file browser and light/dark themes.
- Windows launcher, local integration tests, and CI checks.
