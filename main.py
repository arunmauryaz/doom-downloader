"""
Doom Downloader entry point.
Supports:
  - Interactive Desktop GUI (default on systems with a graphical display)
  - Headless CLI with easy human commands: download, info, formats, check
  - Quick positional syntax: python main.py <url> [quality] [path]
  - Headless REST API Server: python main.py --server
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
    if len(sys.argv) > 1 and sys.argv[1] in ("--server", "-s", "server"):
        from core.server import main as server_main
        sys.argv.pop(1)
        server_main()
        return

    # 2. CLI mode
    # If any arguments are provided (and it's not an explicit request for GUI)
    if len(sys.argv) > 1:
        if sys.argv[1] not in ("--gui", "-g", "gui"):
            from core.cli import main as cli_main
            args = [arg for arg in sys.argv[1:] if arg not in ("--cli", "-c")]
            sys.exit(cli_main(args))

    # 3. Default: Desktop GUI Frontend
    # If running on a headless Linux/Unix machine with no display server, don't crash with TclError
    if sys.platform != "win32" and not (os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY")):
        print("\n=======================================================")
        print(" Doom Downloader — Headless Environment Detected")
        print("=======================================================")
        print("No graphical display found ($DISPLAY / $WAYLAND_DISPLAY not set).")
        print("\nRun via CLI:")
        print("  python main.py download <url> [quality] [path]")
        print("  python main.py <url> [quality] [path]")
        print("  python main.py info <url>")
        print("  python main.py formats")
        print("  python main.py check")
        print("  python main.py --help\n")
        sys.exit(0)

    try:
        from core import DoomEngine
        from gui.app import DownloaderApp

        engine = DoomEngine()
        if engine.is_ffmpeg_ready():
            print(f"[Doom Downloader] FFmpeg: {engine.ffmpeg_dir}")
        else:
            print("[Doom Downloader] Warning: FFmpeg not detected in bin or PATH.")

        app = DownloaderApp(downloader=engine.downloader, queue_manager=engine.queue_manager)
        app.mainloop()
    except Exception as e:
        print(f"\n[Doom Downloader] Could not launch graphical desktop interface: {e}")
        print("Falling back to CLI mode. Run 'python main.py --help' for commands.\n")
        from core.cli import main as cli_main
        sys.exit(cli_main(["--help"]))


if __name__ == "__main__":
    main()
