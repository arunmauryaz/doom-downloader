"""
Doom Downloader Engine Core.
Completely standalone media and direct file downloading backend engine.
Zero GUI dependencies.
"""

from .engine import DoomEngine
from .downloader import AudioDownloader, DownloadCancelledException, find_ffmpeg_dir
from .queue_manager import QueueManager, DownloadItem, QueueItemStatus
from .direct import download_file, safe_filename
from .formats import (
    FORMAT_NAMES, VIDEO_FORMAT_NAMES, AUDIO_FORMATS, VIDEO_FORMATS,
    DEFAULT_FORMAT, FILE_FORMAT, get_format_info
)
from .url_parser import (
    extract_urls_from_text, is_playlist_url, fetch_playlist_entries, clean_video_url
)
from .spotify import (
    is_spotify_url, is_spotify_playlist_or_album, fetch_spotify_track,
    fetch_spotify_collection, resolve_spotify_to_youtube
)
from .config import config

# Alias
MediaDownloader = AudioDownloader

__all__ = [
    "DoomEngine",
    "AudioDownloader",
    "MediaDownloader",
    "QueueManager",
    "DownloadItem",
    "QueueItemStatus",
    "DownloadCancelledException",
    "find_ffmpeg_dir",
    "download_file",
    "safe_filename",
    "FORMAT_NAMES",
    "VIDEO_FORMAT_NAMES",
    "AUDIO_FORMATS",
    "VIDEO_FORMATS",
    "DEFAULT_FORMAT",
    "FILE_FORMAT",
    "get_format_info",
    "extract_urls_from_text",
    "is_playlist_url",
    "fetch_playlist_entries",
    "clean_video_url",
    "is_spotify_url",
    "is_spotify_playlist_or_album",
    "fetch_spotify_track",
    "fetch_spotify_collection",
    "resolve_spotify_to_youtube",
    "config",
]
