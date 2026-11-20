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
from .scraper import detect_and_resolve_media


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

    # ---------------- Universal Media & URL Resolution ----------------

    def resolve_url(self, url: str, expand_collection: bool = False) -> Dict[str, Any]:
        """
        Inspects and resolves metadata for any supported URL without downloading.
        Identifies whether the URL is Spotify, YouTube, generic web video, or direct file.
        Uses universal web scraper for arbitrary websites.
        """
        detected = detect_and_resolve_media(
            url=url,
            ffmpeg_dir=self.ffmpeg_dir,
            expand_collections=expand_collection
        )
        # Ensure backward compatibility with existing keys
        detected["suggested_mode"] = (
            "File" if detected["media_type"] == "direct_file"
            else "Video" if detected["media_type"] == "video"
            else "Audio"
        )
        if detected["media_type"] == "direct_file":
            detected["type"] = "direct"
        elif detected["media_type"] == "spotify_audio":
            detected["type"] = "spotify"
        else:
            detected["type"] = detected["media_type"]
        return detected

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
        Synchronously downloads a media link, web video, or direct file.
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

        # Pre-download duplicate detection for audio & video
        fmt_info = get_format_info(format_label)
        target_ext = fmt_info.get("ext", "")
        if skip_existing and target_ext:
            from .downloader import find_existing_media
            existing_candidate = None
            try:
                if is_spotify_url(url):
                    s_info = fetch_spotify_track(url)
                    if s_info:
                        stitle = s_info.get("title", "")
                        sartist = s_info.get("artist", "")
                        existing_candidate = find_existing_media(
                            download_dir=target_dir,
                            title=stitle,
                            format_label=format_label,
                            url=url,
                            ffmpeg_dir=self.ffmpeg_dir
                        )
                        if not existing_candidate and sartist:
                            existing_candidate = find_existing_media(
                                download_dir=target_dir,
                                title=f"{sartist} - {stitle}",
                                format_label=format_label,
                                url=url,
                                ffmpeg_dir=self.ffmpeg_dir
                            )
                elif fmt_info.get("kind") == "video":
                    v_info = self.downloader.fetch_video_info(url)
                    v_title = v_info.get("title", "")
                    v_id = v_info.get("id", "")
                    existing_candidate = find_existing_media(
                        download_dir=target_dir,
                        title=v_title,
                        format_label=format_label,
                        source_id=v_id,
                        url=url,
                        ffmpeg_dir=self.ffmpeg_dir
                    )
                else:
                    a_info = self.downloader.fetch_video_info(url)
                    a_title = a_info.get("title", "")
                    a_uploader = a_info.get("uploader", "")
                    existing_candidate = find_existing_media(
                        download_dir=target_dir,
                        title=a_title,
                        format_label=format_label,
                        url=url,
                        ffmpeg_dir=self.ffmpeg_dir
                    )
                    if not existing_candidate and a_uploader:
                        existing_candidate = find_existing_media(
                            download_dir=target_dir,
                            title=f"{a_uploader} - {a_title}",
                            format_label=format_label,
                            url=url,
                            ffmpeg_dir=self.ffmpeg_dir
                        )
            except Exception:
                existing_candidate = None

            if existing_candidate and os.path.isfile(existing_candidate):
                if progress_callback:
                    progress_callback({
                        "status": "exists",
                        "percent": 100.0,
                        "message": f"Media already downloaded at {existing_candidate} • Skipped re-download",
                        "filepath": existing_candidate
                    })
                return os.path.abspath(existing_candidate)

        # Mode B: Audio conversion requested for a video (e.g. "[Audio] MP3 (320 kbps)")
        if format_label.startswith("[Audio] "):
            actual_audio_fmt = format_label.replace("[Audio] ", "", 1)
            return self.downloader.download_audio(
                url=url,
                download_dir=target_dir,
                format_label=actual_audio_fmt,
                embed_thumbnail=embed_thumbnail,
                add_metadata=add_metadata,
                crop_square=crop_square,
                progress_callback=progress_callback,
                cancel_event=cancel_event
            )

        # Mode C: Spotify Track -> Match YouTube Audio -> Download & Tag
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

        download_url = url
        from .bilibili import is_bilibili_url, clean_bilibili_url
        if is_bilibili_url(download_url):
            download_url = clean_bilibili_url(download_url)

        # Mode D: Video format
        fmt_info = get_format_info(format_label)
        if fmt_info.get("kind") == "video":
            try:
                return self.downloader.download_video(
                    url=download_url,
                    download_dir=target_dir,
                    format_label=format_label,
                    add_metadata=add_metadata,
                    progress_callback=progress_callback,
                    cancel_event=cancel_event
                )
            except Exception as initial_err:
                resolved = self.resolve_url(url)
                if resolved.get("stream_url") and resolved["stream_url"] != url:
                    return self.downloader.download_video(
                        url=resolved["stream_url"],
                        download_dir=target_dir,
                        format_label=format_label,
                        add_metadata=add_metadata,
                        progress_callback=progress_callback,
                        cancel_event=cancel_event,
                        http_headers=resolved.get("http_headers", {})
                    )
                raise initial_err

        # Mode E: Audio format
        try:
            return self.downloader.download_audio(
                url=download_url,
                download_dir=target_dir,
                format_label=format_label,
                embed_thumbnail=embed_thumbnail,
                add_metadata=add_metadata,
                crop_square=crop_square,
                progress_callback=progress_callback,
                cancel_event=cancel_event
            )
        except Exception as initial_err:
            resolved = self.resolve_url(url)
            if resolved.get("stream_url") and resolved["stream_url"] != url:
                return self.downloader.download_audio(
                    url=resolved["stream_url"],
                    download_dir=target_dir,
                    format_label=format_label,
                    embed_thumbnail=embed_thumbnail,
                    add_metadata=add_metadata,
                    crop_square=crop_square,
                    progress_callback=progress_callback,
                    cancel_event=cancel_event,
                    http_headers=resolved.get("http_headers", {})
                )
            raise initial_err

    # ---------------- Asynchronous Queue Dispatch ----------------

    def enqueue(
        self,
        url: str,
        format_label: str = DEFAULT_FORMAT,
        download_dir: Optional[str] = None,
        title: str = "Resolving track...",
        artist: str = "Web",
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
        format_label: Optional[str] = None,
        download_dir: Optional[str] = None,
        expand_collections: bool = True,
        skip_existing: bool = True,
        embed_thumbnail: bool = True,
        add_metadata: bool = True
    ) -> List[DownloadItem]:
        """
        Parses text or list of URLs, auto-detects media types, expands collections,
        and enqueues items with smart defaults or specified format.
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
            # 1. Expand collections/playlists if requested
            if expand_collections and is_playlist_url(url):
                try:
                    title, entries = fetch_playlist_entries(url, self.ffmpeg_dir)
                    for entry in entries:
                        chosen_fmt = format_label or "MP4 · Best available"
                        item = self.queue_manager.add_item(
                            url=entry["url"],
                            format_label=chosen_fmt,
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

            # 2. Single item: Detect smart default if format_label not provided
            clean = clean_video_url(url)
            is_spot = is_spotify_url(clean)
            if not format_label:
                detected = self.resolve_url(clean)
                chosen_fmt = detected.get("default_format", DEFAULT_FORMAT)
                artist = detected.get("artist") or detected.get("platform", "Web")
                title = detected.get("title") or "Resolving track..."
                thumb = detected.get("thumbnail_url", "")
            else:
                chosen_fmt = format_label
                artist = "Spotify" if is_spot else "Web"
                title = "Resolving track..."
                thumb = ""

            item = self.queue_manager.add_item(
                url=clean,
                format_label=chosen_fmt,
                download_dir=target_dir,
                title=title,
                artist=artist,
                thumbnail_url=thumb,
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
        """Returns aggregate queue statistics."""
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
        self.queue_manager.pause()

    def resume(self):
        self.queue_manager.resume()

    def pause_item(self, item_id: str):
        self.queue_manager.pause_item(item_id)

    def resume_item(self, item_id: str):
        self.queue_manager.resume_item(item_id)

    def cancel(self, item_id: str):
        self.queue_manager.cancel_item(item_id)

    def retry(self, item_id: str):
        self.queue_manager.retry_item(item_id)

    def remove(self, item_id: str) -> bool:
        return self.queue_manager.remove_item(item_id)

    def clear_completed(self) -> List[str]:
        return self.queue_manager.clear_completed()

    def stop(self):
        self.queue_manager.stop()
