"""
IDM-Style High-Performance Multi-Segmented File Downloader.
Features:
  - Parallel multi-connection downloading (up to 8-16 simultaneous threads)
  - HTTP Range byte-splitting for maximum network packet saturation
  - Dynamic pause, resume, and retry capability (.doompart & .doomstate)
  - Instantaneous speed calculation (MB/s) and precise ETA tracking
  - Graceful fallback for single-stream / non-range servers
"""

import json
import mimetypes
import os
import re
import threading
import time
from email.message import Message
from typing import Callable, Dict, Any, List, Optional, Tuple
from urllib.parse import unquote, urlsplit

import requests

BROWSER_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0.0.0 Safari/537.36 DoomDownloader/1.2"
)


def safe_filename(name: str) -> str:
    """Sanitizes filename for cross-platform filesystem safety."""
    name = re.sub(r'[<>:"/\\|?*\x00-\x1f]', '_', name).strip(' .')[:180]
    if not name:
        name = 'download'
    reserved = {'CON', 'PRN', 'AUX', 'NUL', *(f'COM{i}' for i in range(1, 10)), *(f'LPT{i}' for i in range(1, 10))}
    if name.split('.')[0].upper() in reserved:
        name = '_' + name
    return name


def _save_state(state_path: str, url: str, total_bytes: int, segments: List[Dict[str, Any]]):
    try:
        temp_state = state_path + ".tmp"
        with open(temp_state, "w", encoding="utf-8") as f:
            json.dump({
                "url": url,
                "total_bytes": total_bytes,
                "updated_at": time.time(),
                "segments": segments
            }, f)
        os.replace(temp_state, state_path)
    except Exception:
        pass


def _load_state(state_path: str, url: str, total_bytes: int) -> Optional[List[Dict[str, Any]]]:
    if not os.path.isfile(state_path):
        return None
    try:
        with open(state_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if data.get("url") == url and data.get("total_bytes") == total_bytes:
            return data.get("segments")
    except Exception:
        pass
    return None


def download_file(
    url: str,
    download_dir: str,
    progress_callback: Optional[Callable[[Dict[str, Any]], None]] = None,
    cancel_event: Optional[threading.Event] = None,
    skip_existing: bool = True,
    max_connections: int = 8
) -> Tuple[str, bool]:
    """
    IDM-style accelerated multi-segment file downloader.
    Splits downloadable files into parallel HTTP Range segments to achieve maximum network speed.
    Supports pausing and resuming without discarding downloaded bytes.
    """
    from .downloader import DownloadCancelledException

    def check_cancel():
        if cancel_event and cancel_event.is_set():
            raise DownloadCancelledException("Download cancelled by user")

    check_cancel()
    target_dir = os.path.abspath(download_dir)
    os.makedirs(target_dir, exist_ok=True)

    # 1. Probe server for Range support, Content-Length, and filename
    probe_headers = {
        "User-Agent": BROWSER_USER_AGENT,
        "Accept-Encoding": "identity",
        "Range": "bytes=0-0"
    }

    try:
        with requests.get(url, stream=True, timeout=(10, 25), headers=probe_headers) as resp:
            check_cancel()
            status_code = resp.status_code
            headers = resp.headers
            final_url = resp.url or url

            # Content-Disposition filename
            message = Message()
            message["Content-Disposition"] = headers.get("Content-Disposition", "")
            filename = message.get_filename()

            content_type = headers.get("Content-Type", "").split(";")[0].lower()
            if content_type in ("text/html", "application/xhtml+xml") and not filename:
                raise ValueError("This link opens a web page. Use Audio or Video for embedded media, or paste a direct file link.")

            if not filename:
                path_part = unquote(urlsplit(final_url).path.rsplit("/", 1)[-1])
                filename = path_part or "download"
                if not os.path.splitext(filename)[1]:
                    filename += mimetypes.guess_extension(content_type) or ".bin"

            filename = safe_filename(filename)
            target_path = os.path.join(target_dir, filename)

            # Skip duplicate check
            if skip_existing and os.path.isfile(target_path):
                return target_path, True

            # Range & Length check
            range_supported = (status_code == 206) or ("bytes" in headers.get("Accept-Ranges", "").lower())
            total_bytes = 0

            # Determine total length from Content-Range (bytes 0-0/TOTAL) or Content-Length
            cr = headers.get("Content-Range", "")
            if cr and "/" in cr:
                try:
                    total_bytes = int(cr.split("/")[-1])
                except ValueError:
                    total_bytes = 0

            if not total_bytes:
                cl = headers.get("Content-Length", "")
                if cl.isdigit():
                    total_bytes = int(cl)
    except Exception as probe_err:
        check_cancel()
        raise probe_err

    part_path = target_path + ".doompart"
    state_path = target_path + ".doomstate"

    # ---------------- Mode A: IDM Multi-Segment Parallel Download ----------------
    if range_supported and total_bytes >= 1024 * 1024:  # >= 1 MB
        num_segments = min(max_connections, max(2, total_bytes // (2 * 1024 * 1024)))
        segments = _load_state(state_path, url, total_bytes)

        if not segments or not os.path.isfile(part_path):
            chunk_size = total_bytes // num_segments
            segments = []
            for s in range(num_segments):
                start = s * chunk_size
                end = (s + 1) * chunk_size - 1 if s < num_segments - 1 else total_bytes - 1
                segments.append({
                    "id": s,
                    "start": start,
                    "current": start,
                    "end": end,
                    "completed": False
                })
            # Pre-allocate part file
            with open(part_path, "wb") as f:
                if total_bytes > 0:
                    f.seek(total_bytes - 1)
                    f.write(b"\0")
            _save_state(state_path, url, total_bytes, segments)

        # Thread coordination
        downloaded_lock = threading.Lock()
        initial_bytes = sum(max(0, seg["current"] - seg["start"]) for seg in segments)
        received_bytes = [initial_bytes]
        stop_workers = threading.Event()
        worker_threads = []

        def worker_task(seg: Dict[str, Any]):
            if seg["completed"] or seg["current"] > seg["end"]:
                return

            with open(part_path, "r+b") as fp:
                retries = 5
                while retries > 0 and not stop_workers.is_set() and not (cancel_event and cancel_event.is_set()):
                    req_start = seg["current"]
                    req_end = seg["end"]
                    if req_start > req_end:
                        seg["completed"] = True
                        break

                    headers = {
                        "User-Agent": BROWSER_USER_AGENT,
                        "Range": f"bytes={req_start}-{req_end}",
                        "Accept-Encoding": "identity"
                    }

                    try:
                        with requests.get(url, headers=headers, stream=True, timeout=(10, 30)) as s_resp:
                            if s_resp.status_code not in (200, 206):
                                retries -= 1
                                time.sleep(0.3)
                                continue

                            for chunk in s_resp.iter_content(chunk_size=128 * 1024):
                                if stop_workers.is_set() or (cancel_event and cancel_event.is_set()):
                                    return
                                if not chunk:
                                    continue

                                fp.seek(seg["current"])
                                fp.write(chunk)
                                chunk_len = len(chunk)
                                seg["current"] += chunk_len

                                with downloaded_lock:
                                    received_bytes[0] += chunk_len

                            if seg["current"] >= seg["end"] + 1:
                                seg["completed"] = True
                                break

                    except Exception:
                        retries -= 1
                        time.sleep(0.3)

        for seg in segments:
            if not seg["completed"]:
                t = threading.Thread(target=worker_task, args=(seg,), daemon=True)
                worker_threads.append(t)
                t.start()

        started_time = time.monotonic()
        last_progress_time = started_time
        last_bytes = initial_bytes
        last_state_save = started_time

        try:
            while any(t.is_alive() for t in worker_threads):
                check_cancel()
                time.sleep(0.1)
                now = time.monotonic()

                # Save state every 1.5 seconds for resume safety
                if now - last_state_save >= 1.5:
                    _save_state(state_path, url, total_bytes, segments)
                    last_state_save = now

                # Dispatch progress
                if progress_callback and (now - last_progress_time >= 0.15):
                    with downloaded_lock:
                        current_total = received_bytes[0]
                    delta = current_total - last_bytes
                    dt = max(now - last_progress_time, 0.001)
                    speed = delta / dt
                    percent = min(100.0, (current_total / total_bytes) * 100.0) if total_bytes > 0 else 0.0
                    eta_sec = int((total_bytes - current_total) / max(speed, 1)) if speed > 0 and total_bytes > 0 else 0
                    eta_str = f"{eta_sec}s" if eta_sec < 60 else f"{eta_sec // 60}m {eta_sec % 60}s"

                    progress_callback({
                        "status": "downloading",
                        "percent": percent,
                        "downloaded_bytes": current_total,
                        "total_bytes": total_bytes,
                        "speed": speed,
                        "speed_str": f"{speed / (1024 * 1024):.1f} MB/s",
                        "eta_str": eta_str,
                        "connections": sum(1 for t in worker_threads if t.is_alive())
                    })
                    last_progress_time = now
                    last_bytes = current_total

            for t in worker_threads:
                t.join(timeout=2.0)
            check_cancel()

        except DownloadCancelledException:
            stop_workers.set()
            if os.path.isfile(part_path):
                try:
                    os.remove(part_path)
                except Exception:
                    pass
            if os.path.isfile(state_path):
                try:
                    os.remove(state_path)
                except Exception:
                    pass
            raise

        # Verify all segments finished
        if not all(seg["completed"] for seg in segments):
            _save_state(state_path, url, total_bytes, segments)
            raise IOError("One or more download segments failed to complete. Retry to resume.")

        # Finish: Atomic replace
        if os.path.isfile(target_path):
            os.remove(target_path)
        os.replace(part_path, target_path)
        if os.path.isfile(state_path):
            try:
                os.remove(state_path)
            except Exception:
                pass

        if progress_callback:
            progress_callback({
                "status": "downloading",
                "percent": 100.0,
                "downloaded_bytes": total_bytes,
                "total_bytes": total_bytes,
                "speed": 0.0,
                "speed_str": "0 MB/s",
                "eta_str": "Done"
            })
        return target_path, False

    # ---------------- Mode B: High-Speed Single Stream Fallback ----------------
    initial_bytes = 0
    mode = "wb"
    headers = {
        "User-Agent": BROWSER_USER_AGENT,
        "Accept-Encoding": "identity"
    }

    if range_supported and os.path.isfile(part_path):
        existing_size = os.path.getsize(part_path)
        if total_bytes > 0 and existing_size < total_bytes:
            headers["Range"] = f"bytes={existing_size}-"
            initial_bytes = existing_size
            mode = "ab"

    received = initial_bytes
    started = time.monotonic()
    last_update = 0

    try:
        with requests.get(url, stream=True, timeout=(15, 30), headers=headers) as response:
            check_cancel()
            if response.status_code not in (200, 206):
                response.raise_for_status()

            with open(part_path, mode) as output:
                for chunk in response.iter_content(chunk_size=128 * 1024):
                    check_cancel()
                    if not chunk:
                        continue
                    output.write(chunk)
                    received += len(chunk)
                    now = time.monotonic()

                    if progress_callback and (now - last_update >= 0.15):
                        speed = (received - initial_bytes) / max(now - started, 0.001)
                        percent = min(100.0, received / total_bytes * 100) if total_bytes else 0.0
                        eta_sec = int((total_bytes - received) / max(speed, 1)) if speed > 0 and total_bytes else 0
                        eta_str = f"{eta_sec}s" if eta_sec < 60 else f"{eta_sec // 60}m {eta_sec % 60}s"

                        progress_callback({
                            "status": "downloading",
                            "percent": percent,
                            "downloaded_bytes": received,
                            "total_bytes": total_bytes,
                            "speed": speed,
                            "speed_str": f"{speed / (1024 * 1024):.1f} MB/s",
                            "eta_str": eta_str if total_bytes else "--",
                            "connections": 1
                        })
                        last_update = now

        check_cancel()
        if total_bytes and received < total_bytes:
            raise IOError("Incomplete response stream. Retry to resume.")

        if os.path.isfile(target_path):
            os.remove(target_path)
        os.replace(part_path, target_path)
        return target_path, False

    except DownloadCancelledException:
        if os.path.isfile(part_path):
            try:
                os.remove(part_path)
            except Exception:
                pass
        if os.path.isfile(state_path):
            try:
                os.remove(state_path)
            except Exception:
                pass
        raise

