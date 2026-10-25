# Changelog

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
