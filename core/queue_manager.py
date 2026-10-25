"""
Download Queue Manager.
Manages concurrent downloads, task lifecycle, stats aggregation, and thread safety.
"""

import os
import uuid
import time
import threading
from typing import List, Dict, Any, Optional, Callable
from concurrent.futures import ThreadPoolExecutor
from .downloader import AudioDownloader, DownloadCancelledException
from .formats import get_format_info
from .config import config
from .spotify import is_spotify_url, fetch_spotify_track, resolve_spotify_to_youtube

class QueueItemStatus:
    QUEUED = "QUEUED"
    FETCHING = "FETCHING"
    DOWNLOADING = "DOWNLOADING"
    CONVERTING = "CONVERTING"
    COMPLETED = "COMPLETED"
    EXISTS = "EXISTS"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"

class DownloadItem:
    def __init__(
        self,
        url: str,
        format_label: str,
        download_dir: str,
        title: str = "Resolving track...",
        artist: str = "YouTube",
        duration: int = 0,
        thumbnail_url: str = "",
        thumbnail_image: Optional[Any] = None,
        embed_thumbnail: bool = True,
        crop_square: bool = True,
        add_metadata: bool = True,
        playlist_name: Optional[str] = None,
        skip_existing: bool = True
    ):
        self.id = str(uuid.uuid4())
        self.url = url
        self.format_label = format_label
        self.download_dir = download_dir
        self.title = title
        self.artist = artist
        self.duration = duration
        self.source_id = ""
        self.thumbnail_url = thumbnail_url
        self.thumbnail_image = thumbnail_image
        self.embed_thumbnail = embed_thumbnail
        self.crop_square = crop_square
        self.add_metadata = add_metadata
        self.playlist_name = playlist_name
        self.skip_existing = skip_existing

        self.status = QueueItemStatus.QUEUED
        self.percent = 0.0
        self.speed = 0.0
        self.speed_str = "0 KB/s"
        self.eta_str = "--:--"
        self.downloaded_bytes = 0
        self.total_bytes = 0
        self.status_message = "Waiting in queue..."
        self.error_message = ""
        self.filepath = ""
        self.added_at = time.time()
        self.finished_at = 0.0
        self.force_redownload = False

        self.cancel_event = threading.Event()

    def cancel(self):
        self.cancel_event.set()
        if self.status in [QueueItemStatus.QUEUED, QueueItemStatus.FETCHING]:
            self.status = QueueItemStatus.CANCELLED
            self.status_message = "Cancelled by user"

    def reset_for_retry(self):
        self.cancel_event.clear()
        self.status = QueueItemStatus.QUEUED
        self.percent = 0.0
        self.speed = 0.0
        self.speed_str = "0 KB/s"
        self.eta_str = "--:--"
        self.status_message = "Retrying in queue..."
        self.error_message = ""
        self.filepath = ""
        self.force_redownload = True

class QueueManager:
    def __init__(self, downloader: AudioDownloader, max_workers: int = 2):
        self.downloader = downloader
        self.max_workers = max_workers
        self.items: List[DownloadItem] = []
        self.lock = threading.RLock()

        self.executor = ThreadPoolExecutor(max_workers=self.max_workers)
        self.is_paused = False
        self._running = True

        # Callbacks
        self.on_item_added: Optional[Callable[[DownloadItem], None]] = None
        self.on_item_updated: Optional[Callable[[DownloadItem], None]] = None
        self.on_stats_updated: Optional[Callable[[Dict[str, Any]], None]] = None

        # Background worker dispatcher
        self._dispatch_thread = threading.Thread(target=self._process_queue_loop, daemon=True)
        self._dispatch_thread.start()

    def add_item(
        self,
        url: str,
        format_label: str,
        download_dir: str,
        title: str = "Resolving track...",
        artist: str = "YouTube",
        duration: int = 0,
        thumbnail_url: str = "",
        thumbnail_image: Optional[Any] = None,
        embed_thumbnail: bool = True,
        crop_square: bool = True,
        add_metadata: bool = True,
        playlist_name: Optional[str] = None,
        skip_existing: bool = True
    ) -> DownloadItem:
        item = DownloadItem(
            url=url,
            format_label=format_label,
            download_dir=download_dir,
            title=title,
            artist=artist,
            duration=duration,
            thumbnail_url=thumbnail_url,
            thumbnail_image=thumbnail_image,
            embed_thumbnail=embed_thumbnail,
            crop_square=crop_square,
            add_metadata=add_metadata,
            playlist_name=playlist_name,
            skip_existing=skip_existing
        )
        with self.lock:
            self.items.append(item)

        if self.on_item_added:
            self.on_item_added(item)

        self._notify_stats()
        return item

    def get_item(self, item_id: str) -> Optional[DownloadItem]:
        with self.lock:
            for item in self.items:
                if item.id == item_id:
                    return item
        return None

    def cancel_item(self, item_id: str):
        item = self.get_item(item_id)
        if item:
            item.cancel()
            if self.on_item_updated:
                self.on_item_updated(item)
            self._notify_stats()

    def retry_item(self, item_id: str):
        item = self.get_item(item_id)
        if item and item.status in [QueueItemStatus.FAILED, QueueItemStatus.CANCELLED, QueueItemStatus.EXISTS]:
            item.reset_for_retry()
            if self.on_item_updated:
                self.on_item_updated(item)
            self._notify_stats()

    def remove_item(self, item_id: str) -> bool:
        with self.lock:
            for i, item in enumerate(self.items):
                if item.id == item_id:
                    item.cancel()
                    self.items.pop(i)
                    self._notify_stats()
                    return True
        return False

    def clear_completed(self) -> List[str]:
        removed_ids = []
        with self.lock:
            remaining = []
            for item in self.items:
                if item.status in [QueueItemStatus.COMPLETED, QueueItemStatus.EXISTS, QueueItemStatus.CANCELLED]:
                    removed_ids.append(item.id)
                else:
                    remaining.append(item)
            self.items = remaining

        self._notify_stats()
        return removed_ids

    def pause(self):
        self.is_paused = True
        self._notify_stats()

    def resume(self):
        self.is_paused = False
        self._notify_stats()

    def _process_queue_loop(self):
        while self._running:
            if not self.is_paused:
                next_item = None
                with self.lock:
                    active_count = sum(
                        1 for i in self.items
                        if i.status in [QueueItemStatus.FETCHING, QueueItemStatus.DOWNLOADING, QueueItemStatus.CONVERTING]
                    )
                    if active_count < self.max_workers:
                        for item in self.items:
                            if item.status == QueueItemStatus.QUEUED:
                                next_item = item
                                item.status = QueueItemStatus.FETCHING
                                break

                if next_item:
                    self.executor.submit(self._execute_download, next_item)
            time.sleep(0.5)

    def _execute_download(self, item: DownloadItem):
        if item.cancel_event.is_set():
            item.status = QueueItemStatus.CANCELLED
            self._notify_item_update(item)
            return

        try:
            if get_format_info(item.format_label).get("kind") == "file":
                self._execute_file(item)
                return
            is_spotify = is_spotify_url(item.url)

            # 1. Fetch info if title is unresolved or thumbnail is missing
            if is_spotify:
                if item.title == "Resolving track..." or not item.thumbnail_url:
                    item.status = QueueItemStatus.FETCHING
                    item.status_message = "Fetching Spotify track details..."
                    self._notify_item_update(item)
                    s_info = fetch_spotify_track(item.url)
                    if s_info:
                        item.title = s_info.get("title", item.title)
                        item.artist = s_info.get("artist", item.artist)
                        item.duration = s_info.get("duration", item.duration)
                        item.thumbnail_url = s_info.get("cover_url", item.thumbnail_url)

                if item.thumbnail_url and not item.thumbnail_image:
                    from .tagger import fetch_thumbnail_jpeg
                    res = fetch_thumbnail_jpeg(item.thumbnail_url, square_crop=item.crop_square)
                    if res:
                        item.thumbnail_image = res[1]
                self._notify_item_update(item)

            else:
                if item.title == "Resolving track..." or not item.thumbnail_image:
                    item.status = QueueItemStatus.FETCHING
                    item.status_message = "Inspecting media…"
                    self._notify_item_update(item)

                    try:
                        info = self.downloader.fetch_video_info(item.url)
                        item.source_id = info.get("id", "")
                        item.title = info.get("title", item.title)
                        item.artist = info.get("uploader", item.artist)
                        item.duration = info.get("duration", item.duration)
                        item.thumbnail_url = info.get("thumbnail", item.thumbnail_url)

                        # Fetch thumbnail for UI card
                        if item.thumbnail_url and not item.thumbnail_image:
                            from .tagger import fetch_thumbnail_jpeg
                            res = fetch_thumbnail_jpeg(item.thumbnail_url, square_crop=item.crop_square)
                            if res:
                                item.thumbnail_image = res[1]
                    except Exception:
                        pass

                    self._notify_item_update(item)

            if item.cancel_event.is_set():
                item.status = QueueItemStatus.CANCELLED
                item.status_message = "Cancelled"
                self._notify_item_update(item)
                return

            # Check if file already exists in destination folder (Duplicate Detection)
            fmt_info = get_format_info(item.format_label)
            target_ext = fmt_info["ext"]
            skip_existing = item.skip_existing

            if skip_existing and not item.force_redownload:
                from .downloader import find_existing_song
                lookup_title = f"{item.title} [{item.source_id}]" if fmt_info.get("kind") == "video" and item.source_id else item.title
                existing_file = find_existing_song(item.download_dir, lookup_title, target_ext)
                if fmt_info.get("kind") != "video" and not existing_file and item.artist and item.artist != "YouTube":
                    existing_file = find_existing_song(item.download_dir, f"{item.artist} - {item.title}", target_ext)

                if existing_file:
                    item.status = QueueItemStatus.EXISTS
                    item.filepath = existing_file
                    item.percent = 100.0
                    item.speed = 0.0
                    item.speed_str = "0 KB/s"
                    item.eta_str = "Found"
                    item.status_message = "Song already exists in destination folder • Skipped re-download"
                    item.finished_at = time.time()
                    self._notify_item_update(item)
                    self._notify_stats()
                    return

            # 2. Resolve download target URL
            target_stream_url = item.url
            if is_spotify:
                item.status = QueueItemStatus.FETCHING
                item.status_message = "Finding audio stream..."
                self._notify_item_update(item)
                yt_url = resolve_spotify_to_youtube(item.artist, item.title, self.downloader.ffmpeg_dir)
                if not yt_url:
                    raise Exception(f"Could not find matching audio for: {item.artist} - {item.title}")
                target_stream_url = yt_url

            # 3. Download and convert
            item.status = QueueItemStatus.DOWNLOADING
            item.status_message = "Downloading…"
            self._notify_item_update(item)

            def progress_callback(data: Dict[str, Any]):
                status = data.get('status')
                if status == 'downloading':
                    item.percent = data.get('percent', 0.0)
                    item.speed = data.get('speed', 0.0)
                    item.speed_str = data.get('speed_str', 'N/A')
                    item.eta_str = data.get('eta_str', 'N/A')
                    item.downloaded_bytes = data.get('downloaded_bytes', 0)
                    item.total_bytes = data.get('total_bytes', 0)
                    item.status_message = f"Downloading: {item.percent}% • {item.speed_str} • ETA {item.eta_str}"
                    self._notify_item_update(item)
                    self._notify_stats()

                elif status == 'converting':
                    item.status = QueueItemStatus.CONVERTING
                    item.percent = 100.0
                    item.speed = 0.0
                    item.speed_str = "0 KB/s"
                    item.eta_str = "Processing"
                    item.status_message = data.get('message', 'Converting format & embedding artwork...')
                    self._notify_item_update(item)
                    self._notify_stats()

                elif status == 'completed':
                    item.filepath = data.get('filepath', '')

            final_path = self.downloader.download_media(
                url=target_stream_url,
                download_dir=item.download_dir,
                format_label=item.format_label,
                embed_thumbnail=item.embed_thumbnail,
                add_metadata=item.add_metadata,
                crop_square=item.crop_square,
                progress_callback=progress_callback,
                cancel_event=item.cancel_event,
                custom_title=item.title if is_spotify else None,
                custom_artist=item.artist if is_spotify else None,
                custom_thumbnail_url=item.thumbnail_url if is_spotify else None
            )

            item.status = QueueItemStatus.COMPLETED
            item.percent = 100.0
            item.filepath = final_path
            item.status_message = "Completed • Saved with cover art"
            item.finished_at = time.time()
            self._notify_item_update(item)

        except DownloadCancelledException:
            item.status = QueueItemStatus.CANCELLED
            item.status_message = "Cancelled by user"
            self._notify_item_update(item)

        except Exception as e:
            item.status = QueueItemStatus.CANCELLED if item.cancel_event.is_set() else QueueItemStatus.FAILED
            item.error_message = str(e)
            item.status_message = f"Failed: {str(e)[:70]}"
            self._notify_item_update(item)

        finally:
            self._notify_stats()

    def _execute_file(self, item):
        from .direct import download_file
        from urllib.parse import urlsplit, unquote
        item.title = unquote(urlsplit(item.url).path.rsplit("/", 1)[-1]) or "File"
        item.artist = urlsplit(item.url).hostname or "HTTP"
        item.status = QueueItemStatus.DOWNLOADING
        item.status_message = "Connecting…"
        self._notify_item_update(item)

        def progress(data):
            for key in ("percent", "speed", "speed_str", "eta_str", "downloaded_bytes", "total_bytes"):
                setattr(item, key, data[key])
            item.status_message = f"{item.speed_str} · {item.eta_str} remaining"
            self._notify_item_update(item)
            self._notify_stats()

        path, exists = download_file(item.url, item.download_dir, progress, item.cancel_event,
                                    item.skip_existing and not item.force_redownload)
        item.filepath = path
        item.title = os.path.basename(path)
        item.status = QueueItemStatus.EXISTS if exists else QueueItemStatus.COMPLETED
        item.status_message = "Already in folder" if exists else "Completed"
        item.percent = 100
        item.speed = 0
        item.finished_at = time.time()
        self._notify_item_update(item)

    def _notify_item_update(self, item: DownloadItem):
        if self.on_item_updated:
            try:
                self.on_item_updated(item)
            except Exception:
                pass

    def _notify_stats(self):
        if not self.on_stats_updated:
            return

        with self.lock:
            total = len(self.items)
            queued = sum(1 for i in self.items if i.status == QueueItemStatus.QUEUED)
            downloading = sum(1 for i in self.items if i.status in [QueueItemStatus.FETCHING, QueueItemStatus.DOWNLOADING, QueueItemStatus.CONVERTING])
            completed = sum(1 for i in self.items if i.status in [QueueItemStatus.COMPLETED, QueueItemStatus.EXISTS])
            exists_count = sum(1 for i in self.items if i.status == QueueItemStatus.EXISTS)
            failed = sum(1 for i in self.items if i.status == QueueItemStatus.FAILED)
            cancelled = sum(1 for i in self.items if i.status == QueueItemStatus.CANCELLED)

            # Aggregate speed
            active_speeds = [i.speed for i in self.items if i.status == QueueItemStatus.DOWNLOADING and i.speed > 0]
            total_speed_bytes = sum(active_speeds)
            if total_speed_bytes > 1024 * 1024:
                speed_str = f"{total_speed_bytes / (1024 * 1024):.2f} MB/s"
            elif total_speed_bytes > 1024:
                speed_str = f"{total_speed_bytes / 1024:.1f} KB/s"
            else:
                speed_str = "0 KB/s"

            stats = {
                "total": total,
                "queued": queued,
                "downloading": downloading,
                "completed": completed,
                "exists": exists_count,
                "failed": failed,
                "cancelled": cancelled,
                "is_paused": self.is_paused,
                "total_speed_str": speed_str
            }

        try:
            self.on_stats_updated(stats)
        except Exception:
            pass

    def stop(self):
        self._running = False
        with self.lock:
            for item in self.items:
                item.cancel()
        self.executor.shutdown(wait=False)
