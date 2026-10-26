"""
Headless CLI & JSON IPC Interface for Doom Downloader Engine.
Allows external frontends (.NET, Avalonia, WPF, Web APIs, Electron, Bash)
to drive the download engine via command-line arguments and standard I/O JSON streams.
"""

import sys
import os
import json
import argparse
import threading
from typing import Dict, Any

from .engine import DoomEngine
from .formats import DEFAULT_FORMAT, FORMAT_NAMES, VIDEO_FORMAT_NAMES, FILE_FORMAT
from .downloader import DownloadCancelledException


def _emit_json(data: Dict[str, Any]):
    """Prints a single line of JSON to stdout and flushes."""
    sys.stdout.write(json.dumps(data, ensure_ascii=False) + "\n")
    sys.stdout.flush()


def main(args=None):
    parser = argparse.ArgumentParser(
        prog="doom-engine",
        description="Doom Downloader Headless Engine — CLI & JSON IPC Interface"
    )

    parser.add_argument("url", nargs="?", help="URL to inspect or download")
    parser.add_argument("-d", "--download", action="store_true", help="Download the specified URL")
    parser.add_argument("-i", "--info", action="store_true", help="Inspect and print URL metadata in JSON")
    parser.add_argument("-f", "--format", default=DEFAULT_FORMAT, help=f"Target format (default: '{DEFAULT_FORMAT}')")
    parser.add_argument("-o", "--dir", default=None, help="Output destination folder")
    parser.add_argument("--json-progress", action="store_true", help="Emit line-delimited JSON progress updates to stdout")
    parser.add_argument("--no-skip-existing", action="store_true", help="Re-download and overwrite existing files")
    parser.add_argument("--no-artwork", action="store_true", help="Disable embedded album cover art")
    parser.add_argument("--no-metadata", action="store_true", help="Disable embedded tags/metadata")
    parser.add_argument("--formats", action="store_true", help="List all available audio, video, and file formats in JSON")
    parser.add_argument("--check", action="store_true", help="Check engine status and FFmpeg availability in JSON")
    parser.add_argument("--expand", action="store_true", help="Expand collection/playlist entries when resolving info")

    parsed = parser.parse_args(args)
    engine = DoomEngine(download_dir=parsed.dir)

    # 1. Status Check
    if parsed.check:
        status = {
            "engine": "Doom Downloader Core",
            "version": "1.0.0",
            "ffmpeg_available": engine.is_ffmpeg_ready(),
            "ffmpeg_path": engine.ffmpeg_dir,
            "default_download_dir": engine.download_dir
        }
        _emit_json(status)
        return 0

    # 2. Formats List
    if parsed.formats:
        _emit_json(engine.get_formats())
        return 0

    if not parsed.url:
        parser.print_help()
        return 1

    # 3. URL Info / Inspection
    if parsed.info:
        try:
            info = engine.resolve_url(parsed.url, expand_collection=parsed.expand)
            _emit_json(info)
            return 0
        except Exception as e:
            _emit_json({"error": str(e), "url": parsed.url})
            return 1

    # 4. Download Execution
    if parsed.download or not parsed.info:
        cancel_event = threading.Event()

        def progress_callback(data: Dict[str, Any]):
            if parsed.json_progress:
                _emit_json({
                    "type": "progress",
                    "status": data.get("status"),
                    "percent": data.get("percent", 0.0),
                    "speed": data.get("speed", 0.0),
                    "speed_str": data.get("speed_str", "--"),
                    "eta_str": data.get("eta_str", "--"),
                    "message": data.get("message", "")
                })
            else:
                pct = data.get("percent", 0.0)
                speed = data.get("speed_str", "")
                sys.stdout.write(f"\rDownloading: {pct:.1f}% | {speed}   ")
                sys.stdout.flush()

        try:
            if parsed.json_progress:
                _emit_json({"type": "started", "url": parsed.url, "format": parsed.format})

            final_path = engine.download(
                url=parsed.url,
                format_label=parsed.format,
                download_dir=parsed.dir,
                progress_callback=progress_callback,
                cancel_event=cancel_event,
                skip_existing=not parsed.no_skip_existing,
                embed_thumbnail=not parsed.no_artwork,
                add_metadata=not parsed.no_metadata
            )

            if parsed.json_progress:
                _emit_json({"type": "completed", "filepath": final_path})
            else:
                sys.stdout.write(f"\n[Completed] Saved to: {final_path}\n")
            return 0

        except DownloadCancelledException:
            if parsed.json_progress:
                _emit_json({"type": "cancelled", "message": "Download cancelled by user"})
            else:
                sys.stdout.write("\n[Cancelled] Download was cancelled.\n")
            return 2

        except Exception as e:
            if parsed.json_progress:
                _emit_json({"type": "error", "message": str(e)})
            else:
                sys.stderr.write(f"\n[Error] {e}\n")
            return 1


if __name__ == "__main__":
    sys.exit(main())
