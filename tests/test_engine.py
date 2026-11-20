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

        # Test pause_item and resume_item facade
        item2 = self.engine.enqueue(
            url="https://example.com/test2.mp3",
            format_label="MP3 (320 kbps)"
        )
        self.engine.pause_item(item2.id)
        self.assertEqual(item2.status, QueueItemStatus.PAUSED)
        self.engine.resume_item(item2.id)
        self.assertEqual(item2.status, QueueItemStatus.QUEUED)
        self.engine.cancel(item2.id)
        self.assertEqual(item2.status, QueueItemStatus.CANCELLED)

        removed = self.engine.clear_completed()
        self.assertIn(item.id, removed)
        self.assertIn(item2.id, removed)
        self.assertEqual(self.engine.get_stats()["total"], 0)

    def test_enqueue_batch(self):
        text = "https://example.com/one.zip https://example.com/two.mp4"
        items = self.engine.enqueue_batch(text, expand_collections=False)
        self.assertEqual(len(items), 2)
        self.assertEqual(self.engine.get_stats()["total"], 2)

    def test_audio_conversion_format_info(self):
        from core.formats import get_format_info
        info = get_format_info("[Audio] MP3 (320 kbps)")
        self.assertEqual(info["ext"], "mp3")
        self.assertEqual(info["codec"], "mp3")

    def test_universal_web_scraper_html_video(self):
        from core.scraper import detect_and_resolve_media
        from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
        import functools

        with tempfile.TemporaryDirectory() as tmp:
            html = (
                '<html><head><title>Awesome Random Clip</title>'
                '<meta property="og:video" content="https://example.org/stream.mp4">'
                '<meta property="og:image" content="https://example.org/thumb.jpg">'
                '</head><body><video src="clip.mp4"></video></body></html>'
            )
            with open(os.path.join(tmp, "video.html"), "w", encoding="utf-8") as f:
                f.write(html)

            server = ThreadingHTTPServer(('127.0.0.1', 0), functools.partial(SimpleHTTPRequestHandler, directory=tmp))
            port = server.server_port
            t = threading.Thread(target=server.serve_forever, daemon=True)
            t.start()
            try:
                res = detect_and_resolve_media(f"http://127.0.0.1:{port}/video.html")
                self.assertEqual(res["media_type"], "video")
                self.assertIn("Awesome Random Clip", res["title"])
                self.assertTrue(any(f.startswith("MP4") for f in res["available_formats"]))
                self.assertTrue(any(f.startswith("[Audio]") for f in res["available_formats"]))
            finally:
                server.shutdown()
                server.server_close()
                t.join()

    def test_multi_resolution_and_format_duplicate_detection(self):
        from core.downloader import find_existing_media

        with tempfile.TemporaryDirectory() as tmp_dir:
            # 1. Simulate an already downloaded 1080p video file (>10KB)
            v1080 = os.path.join(tmp_dir, "My Song [x123] [1080p].mp4")
            with open(v1080, "wb") as f:
                f.write(b"x" * 20480)

            # Requesting 1080p again should detect existing file
            found_1080 = find_existing_media(tmp_dir, "My Song", "MP4 · 1080p", source_id="x123")
            self.assertIsNotNone(found_1080)
            self.assertEqual(os.path.abspath(found_1080), os.path.abspath(v1080))

            # Requesting 720p or 480p should NOT match 1080p (it must download the new resolution)
            found_720 = find_existing_media(tmp_dir, "My Song", "MP4 · 720p", source_id="x123")
            self.assertIsNone(found_720)

            found_480 = find_existing_media(tmp_dir, "My Song", "MP4 · 480p", source_id="x123")
            self.assertIsNone(found_480)

            # Requesting Audio (MP3) should NOT match 1080p video
            found_audio = find_existing_media(tmp_dir, "My Song", "MP3 (320 kbps)", source_id="x123")
            self.assertIsNone(found_audio)

            # 2. Simulate downloading 720p as well
            v720 = os.path.join(tmp_dir, "My Song [x123] [720p].mp4")
            with open(v720, "wb") as f:
                f.write(b"y" * 20480)

            # Now both 1080p and 720p coexist and are separately recognized
            self.assertEqual(os.path.abspath(find_existing_media(tmp_dir, "My Song", "MP4 · 1080p", source_id="x123")), os.path.abspath(v1080))
            self.assertEqual(os.path.abspath(find_existing_media(tmp_dir, "My Song", "MP4 · 720p", source_id="x123")), os.path.abspath(v720))

            # Audio still does not match
            self.assertIsNone(find_existing_media(tmp_dir, "My Song", "MP3 (320 kbps)", source_id="x123"))

            # 3. Simulate downloading MP3 audio
            a_mp3 = os.path.join(tmp_dir, "My Song.mp3")
            with open(a_mp3, "wb") as f:
                f.write(b"z" * 20480)

            # MP3 matches, but FLAC or WAV does not match MP3
            self.assertEqual(os.path.abspath(find_existing_media(tmp_dir, "My Song", "MP3 (320 kbps)", source_id="x123")), os.path.abspath(a_mp3))
            self.assertIsNone(find_existing_media(tmp_dir, "My Song", "FLAC (Lossless)", source_id="x123"))


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

    def test_resolve_format_aliases(self):
        from core.formats import resolve_format_alias
        self.assertEqual(resolve_format_alias("1080p", media_type="video"), "MP4 · 1080p")
        self.assertEqual(resolve_format_alias("720p", media_type="video"), "MP4 · 720p")
        self.assertEqual(resolve_format_alias("4k", media_type="video"), "MP4 · 2160p")
        self.assertEqual(resolve_format_alias("best", media_type="video"), "MP4 · Best available")
        self.assertEqual(resolve_format_alias("mp3", media_type="video"), "[Audio] MP3 (320 kbps)")
        self.assertEqual(resolve_format_alias("mp3", media_type="audio"), "MP3 (320 kbps)")
        self.assertEqual(resolve_format_alias("wav", media_type="audio"), "WAV (Lossless PCM)")
        self.assertEqual(resolve_format_alias("flac", media_type="video"), "[Audio] FLAC (Lossless)")
        self.assertEqual(resolve_format_alias(None, media_type="video"), "MP4 · Best available")
        self.assertEqual(resolve_format_alias(None, media_type="spotify_audio"), "MP3 (320 kbps)")
        self.assertEqual(resolve_format_alias(None, media_type="direct_file"), "Original file")

    def test_cli_subcommands_and_human_output(self):
        import io
        import sys
        old_stdout = sys.stdout
        sys.stdout = io.StringIO()
        try:
            # check command
            code = cli_main(["check"])
            self.assertEqual(code, 0)
            self.assertIn("Doom Downloader Engine Check", sys.stdout.getvalue())

            # formats command
            sys.stdout = io.StringIO()
            code = cli_main(["formats"])
            self.assertEqual(code, 0)
            self.assertIn("Supported Formats & CLI Aliases", sys.stdout.getvalue())

            # check --json
            sys.stdout = io.StringIO()
            code = cli_main(["check", "--json"])
            self.assertEqual(code, 0)
            data = json.loads(sys.stdout.getvalue().strip())
            self.assertIn("ffmpeg_available", data)
        finally:
            sys.stdout = old_stdout

    def test_cli_download_direct_file(self):
        from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
        import functools
        with tempfile.TemporaryDirectory() as tmp_serve, tempfile.TemporaryDirectory() as tmp_dest:
            test_file = os.path.join(tmp_serve, "sample.txt")
            with open(test_file, "w", encoding="utf-8") as f:
                f.write("Doom Downloader CLI works perfectly!")

            server = ThreadingHTTPServer(('127.0.0.1', 0), functools.partial(SimpleHTTPRequestHandler, directory=tmp_serve))
            port = server.server_port
            t = threading.Thread(target=server.serve_forever, daemon=True)
            t.start()
            try:
                url = f"http://127.0.0.1:{port}/sample.txt"
                code = cli_main(["download", url, tmp_dest])
                self.assertEqual(code, 0)
                downloaded = os.path.join(tmp_dest, "sample.txt")
                self.assertTrue(os.path.isfile(downloaded))
                with open(downloaded, "r", encoding="utf-8") as f:
                    self.assertEqual(f.read(), "Doom Downloader CLI works perfectly!")
            finally:
                server.shutdown()
                server.server_close()
                t.join()

    def test_multisegment_range_download_and_resume(self):
        from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
        import functools
        import re
        from core.direct import download_file

        class RangeHandler(SimpleHTTPRequestHandler):
            def log_message(self, *args):
                pass
            def end_headers(self):
                self.send_header('Accept-Ranges', 'bytes')
                super().end_headers()
            def do_GET(self):
                rh = self.headers.get('Range')
                p = self.translate_path(self.path)
                if not os.path.isfile(p) or not rh:
                    return super().do_GET()
                m = re.search(r'bytes=(\d+)-(\d*)', rh)
                if not m:
                    return super().do_GET()
                fs = os.path.getsize(p)
                start = int(m.group(1))
                end = int(m.group(2)) if m.group(2) else fs - 1
                end = min(end, fs - 1)
                self.send_response(206)
                self.send_header('Content-Type', 'application/octet-stream')
                self.send_header('Content-Range', f'bytes {start}-{end}/{fs}')
                self.send_header('Content-Length', str(end - start + 1))
                self.end_headers()
                with open(p, 'rb') as f:
                    f.seek(start)
                    self.wfile.write(f.read(end - start + 1))

        with tempfile.TemporaryDirectory() as tmp_serve, tempfile.TemporaryDirectory() as tmp_dest:
            # 2 MB payload (triggers multi-segment IDM mode)
            payload = b"X" * (2 * 1024 * 1024)
            test_file = os.path.join(tmp_serve, "bigfile.bin")
            with open(test_file, "wb") as f:
                f.write(payload)

            server = ThreadingHTTPServer(('127.0.0.1', 0), functools.partial(RangeHandler, directory=tmp_serve))
            port = server.server_port
            t = threading.Thread(target=server.serve_forever, daemon=True)
            t.start()
            try:
                url = f"http://127.0.0.1:{port}/bigfile.bin"
                # Part 1: Full multi-segment download
                saved, existed = download_file(url, tmp_dest, max_connections=4)
                self.assertFalse(existed)
                self.assertTrue(os.path.isfile(saved))
                self.assertEqual(os.path.getsize(saved), len(payload))
                with open(saved, "rb") as f:
                    self.assertEqual(f.read(), payload)

                # Part 2: Re-download with skip_existing=False
                saved2, existed2 = download_file(url, tmp_dest, max_connections=4, skip_existing=False)
                self.assertFalse(existed2)
                self.assertTrue(os.path.isfile(saved2))
                self.assertEqual(os.path.getsize(saved2), len(payload))
            finally:
                server.shutdown()
                server.server_close()
                t.join()


    def test_steam_game_scraper(self):
        from core.scraper import detect_and_resolve_media
        res = detect_and_resolve_media("https://store.steampowered.com/app/400/Portal/")
        self.assertEqual(res["platform"], "Steam")
        self.assertEqual(res["media_type"], "video")
        self.assertIn("Portal", res["title"])
        self.assertTrue(res.get("stream_url", "").startswith("http"))




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
