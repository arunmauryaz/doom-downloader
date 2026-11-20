"""
Headless CLI & JSON IPC Interface for Doom Downloader Engine.
Supports:
  - Easy human commands: download, info, formats, check
  - Quick positional syntax: download <url> [quality] [path]
  - Direct URL invocation: <url> [quality] [path]
  - Headless usage on Linux/macOS/Windows, SSH sessions, and containers
  - Machine-readable JSON IPC for external frontends (.NET, Avalonia, Electron, Web APIs, Bash)
"""

import sys
import os
import json
import argparse
import threading
from typing import Dict, Any, List, Optional

from .engine import DoomEngine
from .formats import (
    DEFAULT_FORMAT, FORMAT_NAMES, VIDEO_FORMAT_NAMES, FILE_FORMAT,
    AUDIO_FORMATS, VIDEO_FORMATS, resolve_format_alias, get_format_info
)
from .downloader import DownloadCancelledException
from .spotify import is_spotify_url, is_spotify_playlist_or_album, fetch_spotify_collection
from .url_parser import is_playlist_url, fetch_playlist_entries


def _emit_json(data: Dict[str, Any]):
    """Prints a single line of JSON to stdout and flushes."""
    sys.stdout.write(json.dumps(data, ensure_ascii=False) + "\n")
    sys.stdout.flush()


def _format_size(num_bytes: float) -> str:
    if num_bytes <= 0:
        return ""
    for unit in ("B", "KB", "MB", "GB"):
        if abs(num_bytes) < 1024.0:
            return f"{num_bytes:.1f} {unit}"
        num_bytes /= 1024.0
    return f"{num_bytes:.1f} TB"


def _format_duration(seconds: int) -> str:
    if not seconds:
        return "--"
    m, s = divmod(int(seconds), 60)
    h, m = divmod(m, 60)
    if h > 0:
        return f"{h}h {m}m {s}s"
    return f"{m}m {s}s"


def _is_path_like(s: str) -> bool:
    """Returns True if string looks like a directory path rather than a quality/format alias."""
    if not s:
        return False
    if os.path.isdir(os.path.expanduser(s)):
        return True
    if s.startswith((".", "/", "~", "\\")) or ("/" in s) or ("\\" in s):
        return True
    if len(s) >= 2 and s[1] == ":" and s[0].isalpha():  # Windows drive letter C:\
        return True
    return False


class TerminalProgress:
    """Handles both interactive terminal progress display and machine-readable JSON progress."""

    def __init__(self, json_mode: bool = False):
        self.json_mode = json_mode
        self.last_percent = -1.0
        self.in_progress = False

    def on_progress(self, data: Dict[str, Any]):
        if self.json_mode:
            _emit_json({
                "type": "progress",
                "status": data.get("status"),
                "percent": data.get("percent", 0.0),
                "speed": data.get("speed", 0.0),
                "speed_str": data.get("speed_str", "--"),
                "eta_str": data.get("eta_str", "--"),
                "message": data.get("message", ""),
                "filepath": data.get("filepath", "")
            })
            return

        status = data.get("status", "")
        if status == "downloading":
            pct = data.get("percent", 0.0)
            speed = data.get("speed_str", "--")
            eta = data.get("eta_str", "--")
            bar_width = 25
            filled = int(bar_width * (pct / 100.0))
            bar = "=" * filled
            if filled < bar_width:
                bar += ">" + " " * (bar_width - filled - 1)
            line = f"\r  [{bar}] {pct:5.1f}% | {speed:>10} | ETA: {eta:<6} "
            sys.stdout.write(line)
            sys.stdout.flush()
            self.in_progress = True
        elif status == "converting":
            msg = data.get("message", "Processing media...")
            sys.stdout.write(f"\r  [Processing] {msg:<45}\n")
            sys.stdout.flush()
            self.in_progress = False
        elif status == "exists":
            msg = data.get("message", "File already exists in folder.")
            sys.stdout.write(f"\r  [Info] {msg}\n")
            sys.stdout.flush()
            self.in_progress = False


def _print_help():
    print("""
===================================================================
 Doom Downloader -- Command Line Interface
===================================================================

EASY COMMANDS:
  python main.py download <url> [quality] [path]
  python main.py <url> [quality] [path]
  python main.py info <url>
  python main.py formats
  python main.py check

EXAMPLES:
  # Download best quality video to default downloads folder
  python main.py download "https://youtube.com/watch?v=..."

  # Download 1080p video directly
  python main.py download "https://youtube.com/watch?v=..." 1080p

  # Download 720p video to a custom folder
  python main.py download "https://youtube.com/watch?v=..." 720p "~/Videos"

  # Convert video to MP3 audio and save to Music folder
  python main.py download "https://youtube.com/watch?v=..." mp3 "~/Music"

  # Download Spotify song as lossless WAV
  python main.py download "https://open.spotify.com/track/..." wav

  # Download direct file
  python main.py download "https://example.com/archive.zip" "~/Downloads"

  # Inspect metadata without downloading
  python main.py info "https://youtube.com/watch?v=..."

OPTIONS:
  -q, --quality, -f, --format <fmt>   Quality/format preset (e.g. 1080p, 720p, 4k, mp3, flac, wav)
  -o, --dir, --output <path>          Output destination directory
  --audio                             Extract audio only from video links
  --overwrite, --no-skip-existing     Force redownload even if file exists
  --no-artwork                        Do not embed cover art / thumbnail
  --no-metadata                       Do not embed ID3/MP4 metadata tags
  --expand                            Expand playlist/collection entries
  --json                              Print output in structured JSON format
  --json-progress                     Emit line-delimited NDJSON progress events
""")



def main(args=None):
    if args is None:
        args = sys.argv[1:]

    # Remove any stray --cli or -c flag
    args = [arg for arg in args if arg not in ("--cli", "-c")]

    if not args:
        _print_help()
        return 1

    # Help requests
    if any(a in ("-h", "--help", "help") for a in args):
        _print_help()
        return 0

    first = args[0].strip()

    # 1. Status / Check Command
    if first in ("check", "--check", "-c", "status", "--status"):
        json_output = ("--json" in args) or (first == "--check")
        target_dir = None
        for i, a in enumerate(args):
            if a in ("-o", "--dir", "--output") and i + 1 < len(args):
                target_dir = args[i + 1]
        engine = DoomEngine(download_dir=target_dir)
        status = {
            "engine": "Doom Downloader Core",
            "version": "1.2.0",
            "ffmpeg_available": engine.is_ffmpeg_ready(),
            "ffmpeg_path": engine.ffmpeg_dir,
            "default_download_dir": engine.download_dir
        }
        if json_output:
            _emit_json(status)
        else:
            print("\n[Doom Downloader Engine Check]")
            print(f"  FFmpeg:        {'Available (' + engine.ffmpeg_dir + ')' if engine.is_ffmpeg_ready() else 'Not detected'}")
            print(f"  Version:       {status['version']}")
            print(f"  Download Dir:  {engine.download_dir}\n")
        return 0

    # 2. Formats List Command
    if first in ("formats", "--formats"):
        json_output = ("--json" in args) or (first == "--formats")
        engine = DoomEngine()
        fmts = engine.get_formats()
        if json_output:
            _emit_json(fmts)
        else:
            print("\n[Supported Formats & CLI Aliases]")
            print("\n  Video Formats (use: best, 4k, 1440p, 1080p, 720p, 480p):")
            for v in fmts.get("video_formats", []):
                print(f"    - {v['label'].replace('·', '-')}")
            print("\n  Audio Formats (use: mp3, 320k, 192k, wav, flac, m4a, opus, ogg):")
            for a in fmts.get("audio_formats", []):
                print(f"    - {a['label']}")
            print("\n  Direct File:")
            print(f"    - {FILE_FORMAT} (use: file, original)\n")
            return 0

        return 0

    # 3. Info / Inspection Command
    if first in ("info", "--info", "-i"):
        json_output = ("--json" in args) or ("--info" in args) or ("-i" in args)
        expand = "--expand" in args
        url = None
        for a in args[1:]:
            if not a.startswith("-"):
                url = a
                break
        if not url:
            print("Error: No URL provided for info command.")
            return 1

        engine = DoomEngine()
        try:
            info = engine.resolve_url(url, expand_collection=expand)
            if json_output:
                _emit_json(info)
            else:
                print("\n[Media Information]")
                print(f"  Title:      {info.get('title', 'Unknown')}")
                if info.get('artist'):
                    print(f"  Artist:     {info.get('artist')}")
                print(f"  Platform:   {info.get('platform', 'Web')}")
                print(f"  Type:       {info.get('media_type', 'unknown')}")
                print(f"  Duration:   {_format_duration(info.get('duration', 0))}")
                if info.get('thumbnail_url'):
                    print(f"  Thumbnail:  {info.get('thumbnail_url')}")
                print(f"  Default:    {info.get('default_format', DEFAULT_FORMAT)}")
                if info.get('is_collection'):
                    entries = info.get('entries', [])
                    print(f"  Collection: {len(entries)} items")
                print("")
            return 0
        except Exception as e:
            if json_output:
                _emit_json({"error": str(e), "url": url})
            else:
                print(f"\n[Error] Inspecting link: {e}\n")
            return 1

    # 4. Download Command (or direct URL invocation)
    raw_args = list(args)
    if raw_args and raw_args[0] in ("download", "-d", "--download"):
        raw_args.pop(0)

    # Parse remaining positional and keyword arguments
    url = None
    pos_quality = None
    pos_dir = None
    explicit_quality = None
    explicit_dir = None
    audio_only = False
    audio_format = None
    overwrite = False
    no_artwork = False
    no_metadata = False
    expand_collection = False
    json_progress = False
    json_output = False

    i = 0
    while i < len(raw_args):
        a = raw_args[i]
        if a in ("-q", "--quality", "-f", "--format") and i + 1 < len(raw_args):
            explicit_quality = raw_args[i + 1]
            i += 2
            continue
        elif a in ("-o", "--dir", "--output") and i + 1 < len(raw_args):
            explicit_dir = raw_args[i + 1]
            i += 2
            continue
        elif a == "--audio":
            audio_only = True
            i += 1
            continue
        elif a == "--audio-format" and i + 1 < len(raw_args):
            audio_format = raw_args[i + 1]
            audio_only = True
            i += 2
            continue
        elif a in ("--overwrite", "--no-skip-existing"):
            overwrite = True
            i += 1
            continue
        elif a == "--no-artwork":
            no_artwork = True
            i += 1
            continue
        elif a == "--no-metadata":
            no_metadata = True
            i += 1
            continue
        elif a == "--expand":
            expand_collection = True
            i += 1
            continue
        elif a == "--json-progress":
            json_progress = True
            i += 1
            continue
        elif a == "--json":
            json_output = True
            i += 1
            continue
        elif not a.startswith("-"):
            # Positional arguments: url -> (quality or path) -> path
            if url is None:
                url = a
            elif pos_quality is None and pos_dir is None:
                if _is_path_like(a):
                    pos_dir = a
                else:
                    pos_quality = a
            elif pos_dir is None:
                pos_dir = a
            i += 1
        else:
            i += 1

    if not url:
        _print_help()
        return 1

    target_quality = explicit_quality or pos_quality or audio_format
    target_dir = explicit_dir or pos_dir
    if target_dir:
        target_dir = os.path.abspath(os.path.expanduser(target_dir))

    engine = DoomEngine(download_dir=target_dir)
    progress_handler = TerminalProgress(json_mode=json_progress)
    cancel_event = threading.Event()

    try:
        # Resolve URL metadata first
        if not json_progress and not json_output:
            sys.stdout.write("[Doom Downloader] Resolving media...\n")
            sys.stdout.flush()

        info = engine.resolve_url(url, expand_collection=expand_collection)
        media_type = info.get("media_type", "video")
        is_coll = info.get("is_collection", False)

        resolved_format = resolve_format_alias(
            alias=target_quality,
            media_type=media_type,
            audio_only=audio_only
        )

        final_dest_dir = target_dir or engine.download_dir

        # Case A: Playlist / Collection Download
        if is_coll and (expand_collection or is_playlist_url(url) or is_spotify_playlist_or_album(url)):
            entries = info.get("entries", [])
            if not entries:
                if is_spotify_url(url):
                    _, entries = fetch_spotify_collection(url)
                elif is_playlist_url(url):
                    _, entries = fetch_playlist_entries(url, engine.ffmpeg_dir)

            total_entries = len(entries)
            if not json_progress and not json_output:
                print(f"\n[Collection Detected] {info.get('title', 'Collection')} ({total_entries} items)")
                print(f"  Target Format:  {resolved_format}")
                print(f"  Destination:    {final_dest_dir}\n")

            downloaded_files = []
            for idx, entry in enumerate(entries, 1):
                item_url = entry.get("url") or url
                item_title = entry.get("title") or f"Item {idx}"
                if not json_progress and not json_output:
                    print(f"[{idx}/{total_entries}] {item_title}")

                try:
                    fp = engine.download(
                        url=item_url,
                        format_label=resolved_format,
                        download_dir=final_dest_dir,
                        progress_callback=progress_handler.on_progress,
                        cancel_event=cancel_event,
                        skip_existing=not overwrite,
                        embed_thumbnail=not no_artwork,
                        add_metadata=not no_metadata
                    )
                    downloaded_files.append(fp)
                    if not json_progress and not json_output:
                        size_str = _format_size(os.path.getsize(fp)) if os.path.isfile(fp) else ""
                        print(f"  [OK] Finished: {os.path.basename(fp)} ({size_str})\n")
                except Exception as item_err:
                    if not json_progress and not json_output:
                        print(f"  [Failed] {item_err}\n")

            if json_output or json_progress:
                _emit_json({
                    "type": "collection_completed",
                    "title": info.get("title"),
                    "total": total_entries,
                    "downloaded": len(downloaded_files),
                    "files": downloaded_files
                })
            else:
                print(f"[OK] Completed collection: {len(downloaded_files)}/{total_entries} items saved to {final_dest_dir}\n")
            return 0

        # Case B: Single Media Item Download
        if not json_progress and not json_output:
            print(f"  Title:     {info.get('title', 'Media')}")
            if info.get('artist'):
                print(f"  Artist:    {info.get('artist')}")
            print(f"  Platform:  {info.get('platform', 'Web')}")
            print(f"  Format:    {resolved_format}")
            print(f"  Output:    {final_dest_dir}\n")

        if json_progress:
            _emit_json({
                "type": "started",
                "url": url,
                "title": info.get("title", ""),
                "format": resolved_format,
                "output_dir": final_dest_dir
            })

        final_path = engine.download(
            url=url,
            format_label=resolved_format,
            download_dir=final_dest_dir,
            progress_callback=progress_handler.on_progress,
            cancel_event=cancel_event,
            skip_existing=not overwrite,
            embed_thumbnail=not no_artwork,
            add_metadata=not no_metadata
        )

        file_size_str = ""
        if os.path.isfile(final_path):
            file_size_str = f" ({_format_size(os.path.getsize(final_path))})"

        if json_output or json_progress:
            _emit_json({
                "type": "completed",
                "url": url,
                "filepath": final_path,
                "format": resolved_format
            })
        else:
            print(f"\n  [OK] Completed: {final_path}{file_size_str}\n")
        return 0

    except DownloadCancelledException:
        if json_progress or json_output:
            _emit_json({"type": "cancelled", "message": "Download cancelled by user"})
        else:
            sys.stdout.write("\n\n[Cancelled] Download was cancelled.\n")
        return 2

    except KeyboardInterrupt:
        if json_progress or json_output:
            _emit_json({"type": "cancelled", "message": "Download interrupted by user (SIGINT)"})
        else:
            sys.stdout.write("\n\n[Cancelled] Download interrupted.\n")
        return 2

    except Exception as e:
        if json_progress or json_output:
            _emit_json({"type": "error", "message": str(e), "url": url})
        else:
            sys.stderr.write(f"\n[Error] {e}\n\n")
        return 1


if __name__ == "__main__":
    sys.exit(main())
