"""
Doom Downloader Engine (Backend Core).
A completely headless, standalone media download and processing engine.
Can be imported by any frontend: CustomTkinter GUI, Web servers (FastAPI/Flask),
.NET / Avalonia / WPF desktop apps (via CLI/IPC), or automated scripts.
"""

import os
import threading
from typing import Optional, Dict, Any, List, Callable

from .config import config
from .downloader import AudioDownloader, find_ffmpeg_dir, DownloadCancelledException
from .queue_manager import QueueManager, DownloadItem, QueueItemStatus
from .formats import (
    FORMAT_NAMES, VIDEO_FORMAT_NAMES, AUDIO_FORMATS, VIDEO_FORMATS,
    DEFAULT_FORMAT, FILE_FORMAT, get_format_info
)
from .direct import download_file
from .spotify import (
    is_spotify_url, is_spotify_playlist_or_album,
    fetch_spotify_track, fetch_spotify_collection, resolve_spotify_to_youtube
)
from .url_parser import (
    extract_urls_from_text, is_playlist_url, fetch_playlist_entries, clean_video_url
)


class DoomEngine:
    """
    Unified high-level facade for the Doom Downloader backend engine.
    Independent of any GUI or display framework.
    """

    def __init__(
        self,
        download_dir: Optional[str] = None,
        max_workers: Optional[int] = None,
        ffmpeg_dir: Optional[str] = None
    ):
        self.download_dir = download_dir or config.get("download_dir") or os.path.abspath("downloads")
        self.ffmpeg_dir = ffmpeg_dir or find_ffmpeg_dir()
        if self.ffmpeg_dir:
            os.environ["PATH"] = self.ffmpeg_dir + os.pathsep + os.environ.get("PATH", "")

        self.downloader = AudioDownloader(ffmpeg_dir=self.ffmpeg_dir)
        workers = max_workers or config.get("max_concurrent_downloads", 2)
        self.queue_manager = QueueManager(downloader=self.downloader, max_workers=workers)

    def is_ffmpeg_ready(self) -> bool:
        """Returns True if FFmpeg is available for conversion and merging."""
        return self.downloader.is_ffmpeg_available()

    # ---------------- Format & Options Query ----------------

    def get_formats(self) -> Dict[str, Any]:
        """Returns all supported audio, video, and file format labels and metadata."""
        return {
            "default_format": DEFAULT_FORMAT,
            "file_format": FILE_FORMAT,
            "audio_formats": [
                {"label": k, "ext": v["ext"], "quality": v.get("quality"), "codec": v.get("codec")}
                for k, v in AUDIO_FORMATS.items()
            ],
            "video_formats": [
                {"label": k, "ext": v["ext"], "height": v.get("height")}
                for k, v in VIDEO_FORMATS.items()
            ]
        }

    # ---------------- URL Resolution & Metadata ----------------

    def resolve_url(self, url: str, expand_collection: bool = False) -> Dict[str, Any]:
        """
        Inspects and resolves metadata for any supported URL without downloading.
        Identifies whether the URL is Spotify, YouTube, direct file, or generic web media.
        """
        clean = url.strip()
        result: Dict[str, Any] = {
            "url": clean,
            "type": "unknown",
            "title": "Unknown",
            "artist": "",
            "duration": 0,
            "thumbnail_url": "",
            "is_collection": False,
            "entries": [],
            "suggested_mode": "Audio"
        }

        # 1. Spotify
        if is_spotify_url(clean):
            result["type"] = "spotify"
            result["suggested_mode"] = "Audio"
            if is_spotify_playlist_or_album(clean):
                result["is_collection"] = True
                if expand_collection:
                    title, tracks = fetch_spotify_collection(clean)
                    result["title"] = title
                    result["entries"] = tracks
                else:
                    title, _ = fetch_spotify_collection(clean)
                    result["title"] = title
            else:
                track = fetch_spotify_track(clean)
                if track:
                    result["title"] = track.get("title", "")
                    result["artist"] = track.get("artist", "")
                    result["duration"] = track.get("duration", 0)
                    result["thumbnail_url"] = track.get("cover_url", "")
            return result

        # 2. Check for created playlist / collection
        if is_playlist_url(clean):
            result["is_collection"] = True
            result["type"] = "youtube" if ("youtube.com" in clean or "youtu.be" in clean) else "generic"
            if expand_collection:
                try:
                    title, entries = fetch_playlist_entries(clean, self.ffmpeg_dir)
                    result["title"] = title
                    result["entries"] = entries
                except Exception as e:
                    result["error"] = str(e)
            return result

        # 3. Direct File Link (heuristic)
        path_lower = clean.split("?")[0].lower()
        file_exts = (
            ".pdf", ".zip", ".tar", ".gz", ".7z", ".rar", ".iso", ".exe", ".msi",
            ".docx", ".xlsx", ".pptx", ".txt", ".csv", ".json", ".xml", ".bin"
        )
        if path_lower.endswith(file_exts):
            result["type"] = "direct"
            result["suggested_mode"] = "File"
            result["title"] = os.path.basename(path_lower)
            return result

        # 4. YouTube or Generic Web Media
        try:
            info = self.downloader.fetch_video_info(clean)
            result["type"] = "youtube" if ("youtube.com" in clean or "youtu.be" in clean) else "generic"
            result["title"] = info.get("title", "")
            result["artist"] = info.get("uploader", "")
            result["duration"] = info.get("duration", 0)
            result["thumbnail_url"] = info.get("thumbnail", "")
            result["suggested_mode"] = "Video"
        except Exception as e:
            # Fallback if yt-dlp couldn't extract single video info
            result["error"] = str(e)

        return result

    # ---------------- Synchronous Download ----------------

    def download(
        self,
        url: str,
        format_label: str = DEFAULT_FORMAT,
        download_dir: Optional[str] = None,
        progress_callback: Optional[Callable[[Dict[str, Any]], None]] = None,
        cancel_event: Optional[threading.Event] = None,
        skip_existing: bool = True,
        embed_thumbnail: bool = True,
        add_metadata: bool = True,
        crop_square: bool = True
    ) -> str:
        """
        Synchronously downloads a media link or direct file.
        Automatically handles audio conversion, video merging, artwork embedding, or file streaming.
        Returns the absolute path of the downloaded file.
        """
        target_dir = os.path.abspath(download_dir or self.download_dir)
        os.makedirs(target_dir, exist_ok=True)

        # Mode A: Direct file download
        if format_label == FILE_FORMAT:
            filepath, _ = download_file(
                url=url,
                download_dir=target_dir,
                progress_callback=progress_callback,
                cancel_event=cancel_event,
                skip_existing=skip_existing
            )
            return filepath

        # Mode B: Spotify Track -> Match YouTube Audio -> Download & Tag
        if is_spotify_url(url):
            spotify_info = fetch_spotify_track(url)
            artist = spotify_info.get("artist", "") if spotify_info else ""
            title = spotify_info.get("title", "") if spotify_info else ""
            cover_url = spotify_info.get("cover_url", "") if spotify_info else ""

            if not artist or not title:
                raise RuntimeError(f"Could not fetch Spotify track info for {url}")

            yt_url = resolve_spotify_to_youtube(artist, title, self.ffmpeg_dir)
            if not yt_url:
                raise RuntimeError(f"Could not find matching audio stream for: {artist} - {title}")

            return self.downloader.download_audio(
                url=yt_url,
                download_dir=target_dir,
                format_label=format_label,
                embed_thumbnail=embed_thumbnail,
                add_metadata=add_metadata,
                crop_square=crop_square,
                progress_callback=progress_callback,
                cancel_event=cancel_event,
                custom_title=title,
                custom_artist=artist,
                custom_thumbnail_url=cover_url
            )

        # Mode C: Video format
        fmt_info = get_format_info(format_label)
        if fmt_info.get("kind") == "video":
            return self.downloader.download_video(
                url=url,
                download_dir=target_dir,
                format_label=format_label,
                add_metadata=add_metadata,
                progress_callback=progress_callback,
                cancel_event=cancel_event
            )

        # Mode D: Audio format
        return self.downloader.download_audio(
            url=url,
            download_dir=target_dir,
            format_label=format_label,
            embed_thumbnail=embed_thumbnail,
            add_metadata=add_metadata,
            crop_square=crop_square,
            progress_callback=progress_callback,
            cancel_event=cancel_event
        )

    # ---------------- Asynchronous Queue Dispatch ----------------

    def enqueue(
        self,
        url: str,
        format_label: str = DEFAULT_FORMAT,
        download_dir: Optional[str] = None,
        title: str = "Resolving track...",
        artist: str = "YouTube",
        duration: int = 0,
        thumbnail_url: str = "",
        embed_thumbnail: bool = True,
        crop_square: bool = True,
        add_metadata: bool = True,
        playlist_name: Optional[str] = None,
        skip_existing: bool = True
    ) -> DownloadItem:
        """Adds a single download to the background queue."""
        target_dir = os.path.abspath(download_dir or self.download_dir)
        return self.queue_manager.add_item(
            url=url,
            format_label=format_label,
            download_dir=target_dir,
            title=title,
            artist=artist,
            duration=duration,
            thumbnail_url=thumbnail_url,
            embed_thumbnail=embed_thumbnail,
            crop_square=crop_square,
            add_metadata=add_metadata,
            playlist_name=playlist_name,
            skip_existing=skip_existing
        )

    def enqueue_batch(
        self,
        text_or_urls: Any,
        format_label: str = DEFAULT_FORMAT,
        download_dir: Optional[str] = None,
        expand_collections: bool = True,
        skip_existing: bool = True,
        embed_thumbnail: bool = True,
        add_metadata: bool = True
    ) -> List[DownloadItem]:
        """
        Parses text or list of URLs, expands any collections if enabled, and enqueues all items.
        Returns list of enqueued DownloadItem instances.
        """
        if isinstance(text_or_urls, str):
            urls = extract_urls_from_text(text_or_urls)
        elif isinstance(text_or_urls, (list, tuple, set)):
            urls = []
            for u in text_or_urls:
                urls.extend(extract_urls_from_text(str(u)))
        else:
            urls = []

        target_dir = os.path.abspath(download_dir or self.download_dir)
        enqueued_items: List[DownloadItem] = []

        for url in urls:
            # Expand collections/playlists if requested
            if expand_collections and is_playlist_url(url):
                try:
                    title, entries = fetch_playlist_entries(url, self.ffmpeg_dir)
                    for entry in entries:
                        item = self.queue_manager.add_item(
                            url=entry["url"],
                            format_label=format_label,
                            download_dir=target_dir,
                            title=entry["title"],
                            artist=entry["uploader"],
                            duration=entry["duration"],
                            thumbnail_url=entry.get("thumbnail_url", ""),
                            embed_thumbnail=embed_thumbnail,
                            add_metadata=add_metadata,
                            playlist_name=title,
                            skip_existing=skip_existing
                        )
                        enqueued_items.append(item)
                    continue
                except Exception:
                    pass

            # Single item
            clean = clean_video_url(url)
            is_spot = is_spotify_url(clean)
            item = self.queue_manager.add_item(
                url=clean,
                format_label=format_label,
                download_dir=target_dir,
                artist="Spotify" if is_spot else "YouTube",
                embed_thumbnail=embed_thumbnail,
                add_metadata=add_metadata,
                skip_existing=skip_existing
            )
            enqueued_items.append(item)

        return enqueued_items

    # ---------------- Queue Controls ----------------

    def get_queue(self) -> List[DownloadItem]:
        """Returns the current list of items in the queue."""
        with self.queue_manager.lock:
            return list(self.queue_manager.items)

    def get_stats(self) -> Dict[str, Any]:
        """Returns aggregate queue statistics (total, queued, active, completed, failed, speed)."""
        with self.queue_manager.lock:
            total = len(self.queue_manager.items)
            queued = sum(1 for i in self.queue_manager.items if i.status == QueueItemStatus.QUEUED)
            downloading = sum(
                1 for i in self.queue_manager.items
                if i.status in [QueueItemStatus.FETCHING, QueueItemStatus.DOWNLOADING, QueueItemStatus.CONVERTING]
            )
            completed = sum(1 for i in self.queue_manager.items if i.status in [QueueItemStatus.COMPLETED, QueueItemStatus.EXISTS])
            failed = sum(1 for i in self.queue_manager.items if i.status == QueueItemStatus.FAILED)
            cancelled = sum(1 for i in self.queue_manager.items if i.status == QueueItemStatus.CANCELLED)
            speed = sum(i.speed for i in self.queue_manager.items if i.status == QueueItemStatus.DOWNLOADING)
            return {
                "total": total,
                "queued": queued,
                "downloading": downloading,
                "completed": completed,
                "failed": failed,
                "cancelled": cancelled,
                "total_speed": speed,
                "is_paused": self.queue_manager.is_paused
            }

    def pause(self):
        """Pauses the queue dispatch."""
        self.queue_manager.pause()

    def resume(self):
        """Resumes the queue dispatch."""
        self.queue_manager.resume()

    def cancel(self, item_id: str):
        """Cancels a queued or active download."""
        self.queue_manager.cancel_item(item_id)

    def retry(self, item_id: str):
        """Retries a failed or cancelled item."""
        self.queue_manager.retry_item(item_id)

    def remove(self, item_id: str) -> bool:
        """Removes an item from the queue."""
        return self.queue_manager.remove_item(item_id)

    def clear_completed(self) -> List[str]:
        """Removes finished, existing, and cancelled items from the queue."""
        return self.queue_manager.clear_completed()

    def stop(self):
        """Gracefully shuts down background queue workers."""
        self.queue_manager.stop()
