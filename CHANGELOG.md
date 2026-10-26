# Changelog

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

### Limitations

- Source distribution; Python and FFmpeg are installed separately.
- Website support depends on yt-dlp. DRM and access restrictions are not bypassed.
- Spotify matches can return a different recording.
- Queue history is session-only. Direct file retries restart from the beginning.
