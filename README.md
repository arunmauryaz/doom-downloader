# Doom Downloader

Doom Downloader is a Python download engine with a desktop app, CLI, and local HTTP API. It handles supported web audio/video, direct HTTP(S) files, metadata, artwork, and queued downloads.

## Mission

Build one reliable, reusable download engine that different applications can share. Website detection, downloads, conversion, queue state, and recovery belong in the engine. Each frontend presents those capabilities in its own interface.

“Universal” describes the direction of the project, not a guarantee that every URL works. Availability depends on the source, extractor support, server behavior, authentication, and content protection. Spotify support matches track metadata to YouTube audio; it does not download Spotify's protected audio stream.

## Start here

- **Agents and contributors:** read [AGENTS.md](AGENTS.md), then [LEDGER.md](LEDGER.md) before changing anything.
- [Architecture](docs/ARCHITECTURE.md): engine ownership, frontend boundaries, and reuse.
- [Engine interfaces](docs/ENGINE_API.md): Python, HTTP, CLI, and integration gaps.
- [Project direction](docs/UNIVERSAL_DOWNLOADER_SPEC.md): current scope and future work.
- [Changelog](docs/CHANGELOG.md): version history; the ledger records development handoffs.

## Current capabilities

- Audio output: MP3, M4A, WAV, FLAC, Opus, and OGG; optional artwork and metadata.
- Video output: MP4, MKV, and WebM with resolution limits.
- Website inspection through yt-dlp and the scraper, including embedded-media discovery.
- Direct files with range-based segmented transfers and partial-download state in the current working tree. Resume depends on server support and needs validation for each affected path.
- Concurrent queue, duplicate checks, cancellation, retries, and desktop file browsing.
- Headless `DoomEngine`, CLI/JSON output, and local REST server.

The current frontend is CustomTkinter. A replacement frontend is future work. The source tree's `VERSION` currently says `1.2.0`; this is not proof that its uncommitted changes have been released or verified. See the ledger for the handoff baseline.

## Run

Requires Python 3.11+ and FFmpeg/FFprobe for media conversion and merging. The desktop launcher targets Windows; other engine environments require separate verification.

```powershell
git clone https://github.com/arunmauryaz/doom-downloader.git
cd doom-downloader
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe main.py
```

Alternatively, run `Launch.bat`. Install FFmpeg/FFprobe on PATH or place their executables in `bin/`; see [bin/README.md](bin/README.md).

Headless commands:

```powershell
python main.py formats
python main.py info "https://example.com/video" --json
python main.py download "https://example.com/file.zip" file
python main.py --server --host 127.0.0.1 --port 8080
```

The HTTP server currently has no authentication and allows all CORS origins. Keep it local during development; remote deployment needs additional access controls.

## Validate

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

Tests cover engine, CLI, server, transfers, media processing, and desktop behavior. Test results belong to a specific revision and environment; do not assume a historical passing count applies to new changes.

## Repository structure

- `core/`: canonical Python download engine and headless adapters.
- `desktop/`: modern desktop application (React, TypeScript, Vite, Tailwind CSS, Electron).
- `gui/`: legacy CustomTkinter desktop interface.
- `docs/`: architecture, engine API specs, changelog, and release notes.
- `tests/`: automated unit and integration checks.
- `bin/`: local FFmpeg and FFprobe binaries.
- `main.py`: engine entrypoint (GUI, CLI, or Server modes).
- `Launch.bat`: one-click desktop application launcher.

[GitHub](https://github.com/arunmauryaz/doom-downloader) · [Releases](https://github.com/arunmauryaz/doom-downloader/releases) · [MIT license](LICENSE)
