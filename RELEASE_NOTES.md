# Doom Downloader v1.0.0

The first public release of Doom Downloader, a Windows desktop app for web media and direct files.

## Included

- Audio, Video, and File modes.
- Audio conversion, video quality presets, and embedded artwork.
- General website media extraction through yt-dlp.
- Direct downloads for documents, images, archives, and other HTTP(S) files.
- Single/Bulk input, concurrent queue, cancellation, retries, and duplicate checks.
- Collapsible file browser and light/dark themes.

## Install

1. Download and extract `doom-downloader-1.0.0-source.zip`.
2. Install Python 3.11 or newer.
3. Install FFmpeg and FFprobe on PATH, or place their executables in `bin/`.
4. Run `Launch.bat`. It creates a virtual environment and installs dependencies.

This is a source release, not a standalone executable. Local settings, environments, downloads, and FFmpeg binaries are excluded. `SHA256SUMS.txt` contains the archive checksum.

## Validation and limits

Thirteen tests pass locally, including HTTP file transfers, embedded media extraction with real FFmpeg, and interface checks. Arbitrary external websites have not all been verified. DRM, login requirements, and site restrictions can prevent downloads; the app does not bypass them.

See the README for controls and supported output formats.
