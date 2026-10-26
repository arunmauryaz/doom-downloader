"""
Doom Downloader entry point.
Supports:
  - Desktop GUI (default, when run without arguments)
  - Headless CLI / JSON IPC (--cli, --info, --download, --formats, --check)
  - Headless REST API Server (--server)
"""

import os
import sys

# Ensure project root is in sys.path
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

# Prepend local bin directory containing ffmpeg.exe & ffprobe.exe
bin_dir = os.path.join(PROJECT_ROOT, "bin")
if os.path.isdir(bin_dir):
    os.environ["PATH"] = bin_dir + os.pathsep + os.environ.get("PATH", "")


def main():
    # 1. Server mode
    if len(sys.argv) > 1 and sys.argv[1] in ("--server", "-s"):
        from core.server import main as server_main
        sys.argv.pop(1)
        server_main()
        return

    # 2. CLI mode
    cli_flags = ("--cli", "-c", "--info", "-i", "--download", "-d", "--formats", "--check")
    if len(sys.argv) > 1 and any(arg in cli_flags for arg in sys.argv[1:]):
        from core.cli import main as cli_main
        args = [arg for arg in sys.argv[1:] if arg not in ("--cli", "-c")]
        sys.exit(cli_main(args))

    # 3. Default: Desktop GUI Frontend
    from core import DoomEngine
    from gui.app import DownloaderApp

    engine = DoomEngine()
    if engine.is_ffmpeg_ready():
        print(f"[Doom Downloader] FFmpeg: {engine.ffmpeg_dir}")
    else:
        print("[Doom Downloader] Warning: FFmpeg not detected in bin or PATH.")

    app = DownloaderApp(downloader=engine.downloader, queue_manager=engine.queue_manager)
    app.mainloop()


if __name__ == "__main__":
    main()
