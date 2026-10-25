# Doom Downloader

A Windows desktop downloader for web media and direct files, built with CustomTkinter, yt-dlp, Requests, and FFmpeg.

## Download options

- **Audio:** MP3 (320 or 192 kbps), M4A, WAV, FLAC, Opus, and OGG Vorbis.
- **Video:** MP4, MKV, and WebM, with best available quality or a resolution cap of 480p, 720p, 1080p, 1440p, or 2160p.
- **File:** direct HTTP(S) downloads in their original format, including documents, images, archives, and installers.
- Embedded audio cover art and optional metadata.
- Single/Bulk input, collection expansion, duplicate preferences, and concurrent downloads.
- General website links use yt-dlp extractors, including generic embedded-media discovery.
- A collapsible file browser with folder navigation, filtering, and file opening.
- Pause/resume queue dispatch, cancel, retry failed items, filter by status, and open downloaded media.
- Light/dark appearance and saved preferences.

## Controls

Choose Audio, Video, or File at the top. Paste a page link for media or a direct download link in File mode. Select an output format and folder, then Download.

- Enter downloads in Single mode.
- Shift+Enter or Ctrl+Shift+Enter adds a line and enables Bulk.
- Pasting multiple links enables Bulk automatically.
- Ctrl+Enter downloads in either mode.
- Files opens the side panel. Home returns to the output folder. File names open in their default applications.
- Collections expands supported playlists or pages containing multiple media items; disable it for a single item.

Website coverage depends on yt-dlp and the page. DRM-protected content, browser-only blob URLs, login-required pages without a supported session, and sites with access restrictions may fail. The app does not import browser cookies or bypass those restrictions. File mode streams direct files; it does not save ordinary HTML pages as if they were downloadable media.

Video quality depends on the source. Resolution presets are upper limits. MP4 selects MP4 video and M4A audio; WebM selects compatible WebM streams. MKV accepts the best available streams. If a compatible stream is unavailable, the item reports an error rather than silently changing formats. Converting compressed audio to WAV or FLAC does not restore lost quality.

Spotify links work in Audio mode: track information is matched to YouTube audio. Spotify video downloads are not supported. Matching can return a different recording.

## Install

Requires Windows, Python 3.11+, and FFmpeg/FFprobe. Download the source ZIP from [Releases](https://github.com/arunmauryaz/doom-downloader/releases) or clone:

```powershell
git clone https://github.com/arunmauryaz/doom-downloader.git
cd doom-downloader
```

Install FFmpeg from the builds linked on the [official download page](https://ffmpeg.org/download.html#build-windows). Put FFmpeg and FFprobe on PATH or copy their executables to `bin/`. Binaries are not bundled.

Double-click `Launch.bat`, or install dependencies and run:

```powershell
python -m pip install -r requirements.txt
python main.py
```

FFmpeg and FFprobe must be in `bin/` or on PATH. Downloads and preferences use your selected folder and `settings.json`.

Pausing stops new queue items from starting; active downloads continue. Cancellation is checked during network progress and between processing stages; a running FFmpeg operation may finish before cancellation takes effect. Partial media downloads are retained for yt-dlp. Incomplete direct file transfers are removed and restart on retry. Duplicate detection uses the filename and container, not a comparison of existing video quality; disable **Skip existing** to replace a video with a new quality preset. Queue history is held for the current session.

## Validation

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

Tests cover format profiles, signed URLs, attachment filenames, duplicates, cancellation, embedded video/audio extraction with real FFmpeg, and interface behavior. HTTP integration tests run against a local server; they do not verify every external website.

## Structure

- `core/direct.py`: streaming direct files with atomic output and cancellation.
- `core/downloader.py`: audio extraction, video stream selection and merging, artwork.
- `core/queue_manager.py`: concurrent queue and lifecycle.
- `core/formats.py`: audio/video profiles.
- `gui/app.py`: download controls and queue view.
- `gui/theme.py`: appearance-aware palette.
- `gui/queue_item_card.py`: progress, playback, and item actions.

Format selection follows the [yt-dlp documentation](https://github.com/yt-dlp/yt-dlp#format-selection).

## License

[MIT](LICENSE). Third-party dependencies retain their own licenses.

See [CHANGELOG.md](CHANGELOG.md) for release history.
