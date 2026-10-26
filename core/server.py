"""
Headless HTTP REST API Server for Doom Downloader Engine.
Enables web frontends (React, Vue, Web apps), remote servers, or external services
to control the download engine over standard HTTP and JSON REST endpoints.
Uses Python's standard library ThreadingHTTPServer (zero additional dependencies).
"""

import sys
import os
import json
import urllib.parse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Optional

from .engine import DoomEngine
from .formats import DEFAULT_FORMAT


class EngineAPIHandler(BaseHTTPRequestHandler):
    engine: DoomEngine

    def _set_headers(self, status: int = 200, content_type: str = "application/json"):
        self.send_response(status)
        self.send_header("Content-Type", f"{content_type}; charset=utf-8")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")
        self.end_headers()

    def do_OPTIONS(self):
        self._set_headers(204)

    def log_message(self, format, *args):
        # Override to suppress noisy default logging, or print cleanly
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
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path.rstrip("/")
        query = urllib.parse.parse_qs(parsed.query)

        # GET / or /api/status
        if path in ("", "/api", "/api/status"):
            stats = self.engine.get_stats()
            self._send_json({
                "service": "Doom Downloader API",
                "version": "1.0.0",
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
                    "speed_str": item.speed_str,
                    "eta_str": item.eta_str,
                    "status_message": item.status_message,
                    "error_message": item.error_message,
                    "filepath": item.filepath
                })
            self._send_json({
                "queue": results,
                "stats": self.engine.get_stats()
            })
            return

        self._send_json({"error": "Endpoint not found"}, status=404)

    def do_POST(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path.rstrip("/")
        body = self._read_json_body()

        # POST /api/download
        if path == "/api/download":
            url = body.get("url", "").strip()
            if not url:
                self._send_json({"error": "Missing 'url' in JSON body"}, status=400)
                return
            format_label = body.get("format", DEFAULT_FORMAT)
            download_dir = body.get("download_dir", None)
            expand = body.get("expand", True)
            skip_existing = body.get("skip_existing", True)

            items = self.engine.enqueue_batch(
                text_or_urls=url,
                format_label=format_label,
                download_dir=download_dir,
                expand_collections=expand,
                skip_existing=skip_existing
            )
            self._send_json({
                "enqueued_count": len(items),
                "item_ids": [i.id for i in items]
            }, status=202)
            return

        # POST /api/queue/pause
        if path == "/api/queue/pause":
            self.engine.pause()
            self._send_json({"message": "Queue paused", "stats": self.engine.get_stats()})
            return

        # POST /api/queue/resume
        if path == "/api/queue/resume":
            self.engine.resume()
            self._send_json({"message": "Queue resumed", "stats": self.engine.get_stats()})
            return

        # POST /api/queue/clear
        if path == "/api/queue/clear":
            removed = self.engine.clear_completed()
            self._send_json({"message": f"Cleared {len(removed)} items", "removed_ids": removed})
            return

        # POST /api/queue/<id>/cancel
        if path.startswith("/api/queue/") and path.endswith("/cancel"):
            parts = path.split("/")
            if len(parts) >= 4:
                item_id = parts[3]
                self.engine.cancel(item_id)
                self._send_json({"message": f"Cancelled item {item_id}"})
                return

        # POST /api/queue/<id>/retry
        if path.startswith("/api/queue/") and path.endswith("/retry"):
            parts = path.split("/")
            if len(parts) >= 4:
                item_id = parts[3]
                self.engine.retry(item_id)
                self._send_json({"message": f"Retried item {item_id}"})
                return

        self._send_json({"error": "Endpoint not found"}, status=404)


def create_server(host: str = "127.0.0.1", port: int = 8080, engine: Optional[DoomEngine] = None) -> ThreadingHTTPServer:
    """Creates a ThreadingHTTPServer configured with the DoomEngine."""
    handler = EngineAPIHandler
    handler.engine = engine or DoomEngine()
    server = ThreadingHTTPServer((host, port), handler)
    return server


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Doom Downloader Headless REST API Server")
    parser.add_argument("--host", default="127.0.0.1", help="Host interface (default: 127.0.0.1)")
    parser.add_argument("--port", type=int, default=8080, help="Port to listen on (default: 8080)")
    parser.add_argument("--dir", default=None, help="Default download destination folder")
    parsed = parser.parse_args()

    engine = DoomEngine(download_dir=parsed.dir)
    server = create_server(host=parsed.host, port=parsed.port, engine=engine)
    print(f"========================================================")
    print(f"  Doom Downloader Engine Server listening on:")
    print(f"  http://{parsed.host}:{parsed.port}/")
    print(f"========================================================")
    print(f"  GET  /api/status")
    print(f"  GET  /api/formats")
    print(f"  GET  /api/info?url=<URL>")
    print(f"  POST /api/download")
    print(f"  GET  /api/queue")
    print(f"========================================================")

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down server...")
        server.shutdown()
        server.server_close()
        engine.stop()


if __name__ == "__main__":
    main()
