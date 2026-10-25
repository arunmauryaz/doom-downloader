"""
Doom Downloader entry point.
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

from core.config import config
from core.downloader import AudioDownloader, find_ffmpeg_dir
from core.queue_manager import QueueManager
from gui.app import DownloaderApp

def main():
    # Detect FFmpeg
    ffmpeg_dir = find_ffmpeg_dir()
    if ffmpeg_dir:
        print(f"[Doom Downloader] FFmpeg: {ffmpeg_dir}")
    else:
        print("[Doom Downloader] Warning: FFmpeg not detected in bin or PATH.")

    downloader = AudioDownloader(ffmpeg_dir=ffmpeg_dir)
    max_workers = config.get("max_concurrent_downloads", 2)
    queue_manager = QueueManager(downloader=downloader, max_workers=max_workers)

    app = DownloaderApp(downloader=downloader, queue_manager=queue_manager)
    app.mainloop()

if __name__ == "__main__":
    main()
