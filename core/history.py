"""
Download History Tracker for Doom Downloader.
Tracks files successfully downloaded by this application so the file manager
only displays items processed by Doom Downloader.
"""

import os
import json
import time
import threading
from typing import List, Dict, Any

HISTORY_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "download_history.json")
_history_lock = threading.Lock()


def _load_history_raw() -> List[Dict[str, Any]]:
    if not os.path.exists(HISTORY_FILE):
        return []
    try:
        with open(HISTORY_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            if isinstance(data, list):
                return data
    except Exception:
        pass
    return []


def _save_history_raw(items: List[Dict[str, Any]]):
    try:
        with open(HISTORY_FILE, "w", encoding="utf-8") as f:
            json.dump(items, f, indent=2, ensure_ascii=False)
    except Exception as e:
        print(f"[History] Error saving history: {e}")


def add_download_record(
    filepath: str,
    title: str = "",
    artist: str = "",
    url: str = "",
    format_label: str = "",
    thumbnail_url: str = "",
    size: int = 0
):
    """Records a downloaded file in persistent history."""
    if not filepath or not os.path.isfile(filepath):
        return

    norm_path = os.path.abspath(filepath)
    filename = os.path.basename(norm_path)
    ext = os.path.splitext(filename)[1].lower().lstrip(".")
    try:
        file_size = os.path.getsize(norm_path) if size <= 0 else size
        file_mtime = os.path.getmtime(norm_path)
    except OSError:
        file_size = size
        file_mtime = time.time()

    record = {
        "name": filename,
        "path": norm_path,
        "title": title or filename,
        "artist": artist or "",
        "url": url,
        "format_label": format_label,
        "thumbnail_url": thumbnail_url,
        "size": file_size,
        "modified": file_mtime,
        "downloaded_at": time.time(),
        "ext": ext
    }

    with _history_lock:
        items = _load_history_raw()
        # Avoid duplicate path entries; update existing
        filtered = [item for item in items if os.path.abspath(item.get("path", "")) != norm_path]
        filtered.insert(0, record)
        # Keep maximum 500 records
        _save_history_raw(filtered[:500])


def get_download_history(check_exists: bool = True) -> List[Dict[str, Any]]:
    """Returns the list of files downloaded by Doom Downloader."""
    with _history_lock:
        items = _load_history_raw()
        if not check_exists:
            return items

        valid_items = []
        changed = False
        for it in items:
            p = it.get("path", "")
            if p and os.path.isfile(p):
                # Update current file size if changed
                try:
                    it["size"] = os.path.getsize(p)
                except OSError:
                    pass
                valid_items.append(it)
            else:
                changed = True

        if changed:
            _save_history_raw(valid_items)

        valid_items.sort(key=lambda x: x.get("downloaded_at", x.get("modified", 0)), reverse=True)
        return valid_items


def clear_download_history():
    with _history_lock:
        _save_history_raw([])


def remove_download_record(filepath: str) -> bool:
    """Removes a specific file record from persistent history."""
    if not filepath:
        return False
    norm_path = os.path.abspath(filepath)
    with _history_lock:
        items = _load_history_raw()
        initial_len = len(items)
        filtered = [item for item in items if os.path.abspath(item.get("path", "")) != norm_path]
        if len(filtered) < initial_len:
            _save_history_raw(filtered)
            return True
    return False
