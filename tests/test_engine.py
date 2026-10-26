"""
Tests for DoomEngine facade, headless CLI, and REST API server.
Ensures the engine operates 100% headlessly with zero GUI dependencies.
"""

import os
import json
import tempfile
import threading
import unittest
from unittest.mock import patch

from core import DoomEngine, QueueItemStatus
from core.cli import main as cli_main
from core.server import create_server


class EngineFacadeTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.engine = DoomEngine(download_dir=self.tmp.name, max_workers=2)
        self.engine.pause()  # Keep paused during unit tests

    def tearDown(self):
        self.engine.stop()
        self.tmp.cleanup()

    def test_formats_listing(self):
        fmts = self.engine.get_formats()
        self.assertIn("audio_formats", fmts)
        self.assertIn("video_formats", fmts)
        self.assertIn("default_format", fmts)
        self.assertIn("file_format", fmts)
        self.assertTrue(any(f["label"].startswith("MP3") for f in fmts["audio_formats"]))
        self.assertTrue(any(f["label"].startswith("MP4") for f in fmts["video_formats"]))

    def test_direct_file_url_resolution(self):
        res = self.engine.resolve_url("https://example.com/files/manual.pdf?token=123")
        self.assertEqual(res["type"], "direct")
        self.assertEqual(res["suggested_mode"], "File")
        self.assertEqual(res["title"], "manual.pdf")

    def test_spotify_url_resolution(self):
        res = self.engine.resolve_url("https://open.spotify.com/track/4cOdK2wGLETKBW3PvgPWqT")
        self.assertEqual(res["type"], "spotify")
        self.assertEqual(res["suggested_mode"], "Audio")
        self.assertFalse(res["is_collection"])
        # Should have extracted Rick Astley title
        self.assertIn("Never Gonna Give You Up", res["title"])

    def test_enqueue_and_stats(self):
        item = self.engine.enqueue(
            url="https://example.com/file.zip",
            format_label="Original file"
        )
        self.assertIsNotNone(item.id)
        self.assertEqual(item.status, QueueItemStatus.QUEUED)

        stats = self.engine.get_stats()
        self.assertEqual(stats["total"], 1)
        self.assertEqual(stats["queued"], 1)
        self.assertTrue(stats["is_paused"])

        self.engine.cancel(item.id)
        self.assertEqual(item.status, QueueItemStatus.CANCELLED)

        removed = self.engine.clear_completed()
        self.assertIn(item.id, removed)
        self.assertEqual(self.engine.get_stats()["total"], 0)

    def test_enqueue_batch(self):
        text = "https://example.com/one.zip https://example.com/two.mp4"
        items = self.engine.enqueue_batch(text, expand_collections=False)
        self.assertEqual(len(items), 2)
        self.assertEqual(self.engine.get_stats()["total"], 2)


class CliAndServerTests(unittest.TestCase):
    def test_cli_check_json(self):
        # Capture stdout
        import io
        import sys
        old_stdout = sys.stdout
        sys.stdout = io.StringIO()
        try:
            code = cli_main(["--check"])
            self.assertEqual(code, 0)
            output = json.loads(sys.stdout.getvalue().strip())
            self.assertIn("engine", output)
            self.assertIn("ffmpeg_available", output)
        finally:
            sys.stdout = old_stdout

    def test_cli_formats_json(self):
        import io
        import sys
        old_stdout = sys.stdout
        sys.stdout = io.StringIO()
        try:
            code = cli_main(["--formats"])
            self.assertEqual(code, 0)
            output = json.loads(sys.stdout.getvalue().strip())
            self.assertIn("audio_formats", output)
            self.assertIn("video_formats", output)
        finally:
            sys.stdout = old_stdout

    def test_server_status_and_formats_endpoints(self):
        import urllib.request
        with tempfile.TemporaryDirectory() as tmp:
            engine = DoomEngine(download_dir=tmp, max_workers=1)
            engine.pause()
            server = create_server(host="127.0.0.1", port=0, engine=engine)
            port = server.server_port
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()

            try:
                # GET /api/status
                with urllib.request.urlopen(f"http://127.0.0.1:{port}/api/status") as resp:
                    self.assertEqual(resp.status, 200)
                    data = json.loads(resp.read().decode())
                    self.assertEqual(data["service"], "Doom Downloader API")
                    self.assertIn("stats", data)

                # GET /api/formats
                with urllib.request.urlopen(f"http://127.0.0.1:{port}/api/formats") as resp:
                    self.assertEqual(resp.status, 200)
                    data = json.loads(resp.read().decode())
                    self.assertIn("audio_formats", data)

            finally:
                server.shutdown()
                server.server_close()
                thread.join()
                engine.stop()


if __name__ == "__main__":
    unittest.main()
