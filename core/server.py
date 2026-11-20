"""
Headless HTTP REST API Server for Doom Downloader Engine.
Enables web frontends (React, Vue, Web apps), desktop frontends (Tauri, Electron),
remote servers, or external services to control the download engine over standard HTTP and JSON REST endpoints.
Uses Python's standard library ThreadingHTTPServer (zero additional dependencies).
"""

import sys
import os
import json
import subprocess
import urllib.parse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Optional, List

from .engine import DoomEngine
from .formats import DEFAULT_FORMAT
from .config import config


def get_engine_version() -> str:
    version_file = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "VERSION")
    if os.path.exists(version_file):
        try:
            with open(version_file, "r", encoding="utf-8") as f:
                v = f.read().strip()
                if v:
                    return v
        except Exception:
            pass
    return "1.2.0"


class EngineAPIHandler(BaseHTTPRequestHandler):
    engine: DoomEngine
    auth_token: Optional[str] = None
    allowed_origins: Optional[List[str]] = None

    def _get_origin(self) -> str:
        return self.headers.get("Origin", "")

    def _is_origin_allowed(self) -> bool:
        if not self.allowed_origins:
            return True
        origin = self._get_origin().rstrip("/")
        if not origin:
            return True
        for allowed in self.allowed_origins:
            norm = allowed.rstrip("/")
            if norm == "*" or origin == norm:
                return True
            if norm.endswith("*") and origin.startswith(norm[:-1]):
                return True
        return False

    def _set_headers(self, status: int = 200, content_type: str = "application/json"):
        self.send_response(status)
        self.send_header("Content-Type", f"{content_type}; charset=utf-8")

        req_origin = self._get_origin()
        if self.allowed_origins:
            if self._is_origin_allowed() and req_origin:
                self.send_header("Access-Control-Allow-Origin", req_origin)
                self.send_header("Vary", "Origin")
            else:
                self.send_header("Access-Control-Allow-Origin", "null")
        else:
            self.send_header("Access-Control-Allow-Origin", "*")

        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")
        self.end_headers()

    def _check_auth(self) -> bool:
        if not self.auth_token:
            return True
        auth_header = self.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            token = auth_header[7:].strip()
            if token == self.auth_token:
                return True
        parsed = urllib.parse.urlparse(self.path)
        qs = urllib.parse.parse_qs(parsed.query)
        if qs.get("token", [""])[0] == self.auth_token:
            return True
        return False

    def do_OPTIONS(self):
        self._set_headers(204)

    def log_message(self, format, *args):
        # Clean server logging
        sys.stdout.write(f"[Server] {self.address_string()} - {format % args}\n")
        sys.stdout.flush()

    def _read_json_body(self) -> dict:
        try:
            length = int(self.headers.get("Content-Length", 0))
            if length > 0:
                body = self.rfile.read(length).decode("utf-8")
                return json.loads(body)
        except Exception:
            pass
        return {}

    def _send_json(self, data: dict, status: int = 200):
        self._set_headers(status)
        payload = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.wfile.write(payload)

    def do_GET(self):
        if not self._is_origin_allowed():
            self._send_json({"error": "Forbidden origin"}, status=403)
            return

        if not self._check_auth():
            self._send_json({"error": "Unauthorized"}, status=401)
            return

        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path.rstrip("/")
        query = urllib.parse.parse_qs(parsed.query)

        # GET / or /api or /api/status
        if path in ("", "/api", "/api/status"):
            stats = self.engine.get_stats()
            self._send_json({
                "service": "Doom Downloader API",
                "version": get_engine_version(),
                "ffmpeg_available": self.engine.is_ffmpeg_ready(),
                "download_dir": self.engine.download_dir,
                "stats": stats
            })
            return

        # GET /api/formats
        if path == "/api/formats":
            self._send_json(self.engine.get_formats())
            return

        # GET /api/info?url=...
        if path == "/api/info":
            target_url = query.get("url", [""])[0]
            if not target_url:
                self._send_json({"error": "Missing 'url' query parameter"}, status=400)
                return
            expand = query.get("expand", ["false"])[0].lower() in ("true", "1")
            try:
                info = self.engine.resolve_url(target_url, expand_collection=expand)
                self._send_json(info)
            except Exception as e:
                self._send_json({"error": str(e)}, status=500)
            return

        # GET /api/queue
        if path == "/api/queue":
            items = self.engine.get_queue()
            results = []
            for item in items:
                results.append({
                    "id": item.id,
                    "url": item.url,
                    "title": item.title,
                    "artist": item.artist,
                    "duration": item.duration,
                    "format_label": item.format_label,
                    "status": item.status,
                    "percent": item.percent,
                    "speed": item.speed,
                    "speed_str": item.speed_str,
                    "eta_str": item.eta_str,
                    "downloaded_bytes": item.downloaded_bytes,
                    "total_bytes": item.total_bytes,
                    "status_message": item.status_message,
                    "error_message": item.error_message,
                    "filepath": item.filepath,
                    "thumbnail_url": item.thumbnail_url
                })
            self._send_json({
                "queue": results,
                "stats": self.engine.get_stats()
            })
            return

        # GET /api/config
        if path == "/api/config":
            self._send_json(config.settings)
            return

        # GET /api/files (list only media downloaded by Doom Downloader)
        if path == "/api/files":
            from .history import get_download_history
            target_dir = os.path.abspath(self.engine.download_dir)
            files = get_download_history(check_exists=True)
            self._send_json({
                "download_dir": target_dir,
                "files": files
            })
            return

        self._send_json({"error": "Endpoint not found"}, status=404)

    def do_POST(self):
        if not self._is_origin_allowed():
            self._send_json({"error": "Forbidden origin"}, status=403)
            return

        if not self._check_auth():
            self._send_json({"error": "Unauthorized"}, status=401)
            return

        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path.rstrip("/")
        body = self._read_json_body()

        # POST /api/download
        if path == "/api/download":
            items_payload = body.get("items", [])
            url = body.get("url", "").strip()
            if not url and not items_payload:
                self._send_json({"error": "Missing 'url' or 'items' in JSON body"}, status=400)
                return
            format_label = body.get("format", DEFAULT_FORMAT)
            download_dir = body.get("download_dir", None)
            expand = body.get("expand", True)
            skip_existing = body.get("skip_existing", True)
            embed_thumbnail = body.get("embed_thumbnail", True)
            add_metadata = body.get("add_metadata", True)

            target_dir = os.path.abspath(download_dir or self.engine.download_dir)

            enqueued_items = []
            if items_payload:
                for itm in items_payload:
                    i_url = itm.get("url") or itm.get("stream_url")
                    if not i_url:
                        continue
                    item = self.engine.queue_manager.add_item(
                        url=i_url,
                        format_label=itm.get("format") or format_label,
                        download_dir=target_dir,
                        title=itm.get("title", "Resolving track..."),
                        artist=itm.get("artist", "Web"),
                        duration=itm.get("duration", 0),
                        thumbnail_url=itm.get("thumbnail_url", ""),
                        embed_thumbnail=embed_thumbnail,
                        add_metadata=add_metadata,
                        skip_existing=skip_existing
                    )
                    enqueued_items.append(item)
            else:
                enqueued_items = self.engine.enqueue_batch(
                    text_or_urls=url,
                    format_label=format_label,
                    download_dir=download_dir,
                    expand_collections=expand,
                    skip_existing=skip_existing,
                    embed_thumbnail=embed_thumbnail,
                    add_metadata=add_metadata
                )

            self._send_json({
                "enqueued_count": len(enqueued_items),
                "item_ids": [i.id for i in enqueued_items]
            }, status=202)
            return

        # POST /api/queue/pause (global queue pause)
        if path == "/api/queue/pause":
            self.engine.pause()
            self._send_json({"message": "Queue paused", "stats": self.engine.get_stats()})
            return

        # POST /api/queue/resume (global queue resume)
        if path == "/api/queue/resume":
            self.engine.resume()
            self._send_json({"message": "Queue resumed", "stats": self.engine.get_stats()})
            return

        # POST /api/queue/clear (clear finished)
        if path == "/api/queue/clear":
            removed = self.engine.clear_completed()
            self._send_json({"message": f"Cleared {len(removed)} items", "removed_ids": removed})
            return

        # Item-specific actions
        if path.startswith("/api/queue/") and len(path.split("/")) >= 4:
            parts = path.split("/")
            item_id = parts[3]
            action = parts[4] if len(parts) >= 5 else ""

            # POST /api/queue/<id>/pause
            if action == "pause":
                self.engine.pause_item(item_id)
                self._send_json({"message": f"Paused item {item_id}"})
                return

            # POST /api/queue/<id>/resume
            if action == "resume":
                self.engine.resume_item(item_id)
                self._send_json({"message": f"Resumed item {item_id}"})
                return

            # POST /api/queue/<id>/cancel
            if action == "cancel":
                self.engine.cancel(item_id)
                self._send_json({"message": f"Cancelled item {item_id}"})
                return

            # POST /api/queue/<id>/retry
            if action == "retry":
                self.engine.retry(item_id)
                self._send_json({"message": f"Retried item {item_id}"})
                return

            # POST /api/queue/<id>/remove
            if action == "remove":
                removed = self.engine.remove(item_id)
                self._send_json({"message": f"Removed item {item_id}", "removed": removed})
                return

        # POST /api/config
        if path == "/api/config":
            for k, v in body.items():
                config.set(k, v)
            if "download_dir" in body:
                self.engine.download_dir = os.path.abspath(body["download_dir"])
            self._send_json({"message": "Config updated", "config": config.settings})
            return

        # POST /api/files/open
        if path == "/api/files/open":
            filepath = body.get("path", "")
            norm_path = os.path.abspath(filepath)
            if not os.path.exists(norm_path):
                self._send_json({"error": "File does not exist"}, status=404)
                return
            try:
                if sys.platform == "win32":
                    os.startfile(norm_path)
                elif sys.platform == "darwin":
                    subprocess.Popen(["open", norm_path])
                else:
                    subprocess.Popen(["xdg-open", norm_path])
                self._send_json({"message": f"Opened {os.path.basename(norm_path)}"})
            except Exception as e:
                self._send_json({"error": f"Failed to open file: {e}"}, status=500)
            return

        # POST /api/files/reveal
        if path == "/api/files/reveal":
            filepath = body.get("path", "")
            norm_path = os.path.abspath(filepath) if filepath else os.path.abspath(self.engine.download_dir)
            if not os.path.exists(norm_path):
                self._send_json({"error": "Path not found"}, status=404)
                return
            try:
                if sys.platform == "win32":
                    clean_norm = os.path.normpath(norm_path)
                    if os.path.isfile(clean_norm):
                        subprocess.Popen(f'explorer /select,"{clean_norm}"')
                    else:
                        subprocess.Popen(f'explorer "{clean_norm}"')
                elif sys.platform == "darwin":
                    subprocess.Popen(["open", "-R" if os.path.isfile(norm_path) else "", norm_path])
                else:
                    subprocess.Popen(["xdg-open", os.path.dirname(norm_path) if os.path.isfile(norm_path) else norm_path])
                self._send_json({"message": "Revealed in file manager"})
            except Exception as e:
                self._send_json({"error": f"Failed to reveal in explorer: {e}"}, status=500)
            return

        # POST /api/files/remove
        if path == "/api/files/remove":
            filepath = body.get("path", "")
            delete_disk = bool(body.get("delete_file", False))
            from .history import remove_download_record
            norm_filepath = os.path.abspath(filepath) if filepath else ""
            removed = remove_download_record(norm_filepath) or (remove_download_record(filepath) if filepath else False)
            deleted_disk = False
            if delete_disk and norm_filepath and os.path.isfile(norm_filepath):
                try:
                    os.remove(norm_filepath)
                    deleted_disk = True
                except Exception as e:
                    print(f"[Doom Server] Failed to delete file from disk: {e}")
            self._send_json({"message": "File record removed", "removed": removed, "deleted_disk": deleted_disk})
            return

        # POST /api/browse-directory
        if path == "/api/browse-directory":
            chosen = ""
            try:
                import tkinter as tk
                from tkinter import filedialog
                root = tk.Tk()
                root.withdraw()
                root.attributes("-topmost", True)
                initial = self.engine.download_dir if os.path.isdir(self.engine.download_dir) else None
                chosen = filedialog.askdirectory(initialdir=initial, title="Select Download Destination Folder")
                root.destroy()
            except Exception:
                pass
            if chosen:
                self._send_json({"selected_dir": os.path.abspath(chosen)})
            else:
                self._send_json({"selected_dir": None})
            return

        self._send_json({"error": "Endpoint not found"}, status=404)


def create_server(
    host: str = "127.0.0.1",
    port: int = 8080,
    engine: Optional[DoomEngine] = None,
    auth_token: Optional[str] = None,
    allowed_origins: Optional[List[str]] = None
) -> ThreadingHTTPServer:
    """Creates a ThreadingHTTPServer configured with the DoomEngine."""
    handler = EngineAPIHandler
    handler.engine = engine or DoomEngine()
    handler.auth_token = auth_token
    handler.allowed_origins = allowed_origins
    server = ThreadingHTTPServer((host, port), handler)
    return server


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Doom Downloader Headless REST API Server")
    parser.add_argument("--host", default="127.0.0.1", help="Host interface (default: 127.0.0.1)")
    parser.add_argument("--port", type=int, default=8080, help="Port to listen on (default: 8080, 0 for dynamic)")
    parser.add_argument("--dir", default=None, help="Default download destination folder")
    parser.add_argument("--token", default=None, help="Optional bearer token for authorization")
    parser.add_argument("--allowed-origins", default=None, help="Comma-separated allowed origins (default: all)")
    parsed = parser.parse_args()

    origins = [o.strip() for o in parsed.allowed_origins.split(",")] if parsed.allowed_origins else None
    engine = DoomEngine(download_dir=parsed.dir)
    server = create_server(
        host=parsed.host,
        port=parsed.port,
        engine=engine,
        auth_token=parsed.token,
        allowed_origins=origins
    )
    assigned_port = server.server_port
    engine_ver = get_engine_version()

    # Handshake line for process consumers (Tauri, Electron, scripts)
    handshake_msg = f"[Doom Server Ready] port={assigned_port} version={engine_ver}"
    if parsed.token:
        # Note: Do not log raw secret token in production logs, but confirm token auth is enabled
        handshake_msg += " auth=bearer"
    print(handshake_msg)
    sys.stdout.flush()

    print(f"========================================================")
    print(f"  Doom Downloader Engine Server listening on:")
    print(f"  http://{parsed.host}:{assigned_port}/ (v{engine_ver})")
    print(f"========================================================")
    print(f"  GET  /api/status")
    print(f"  GET  /api/formats")
    print(f"  GET  /api/info?url=<URL>")
    print(f"  POST /api/download")
    print(f"  GET  /api/queue")
    print(f"  GET  /api/files")
    print(f"========================================================")
    sys.stdout.flush()

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down server...")
        server.shutdown()
        server.server_close()
        engine.stop()


if __name__ == "__main__":
    main()
