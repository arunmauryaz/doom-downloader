import functools
import os
from pathlib import Path
import subprocess
import tempfile
import threading
import unittest
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer

from core.direct import download_file, safe_filename
from core.downloader import AudioDownloader, DownloadCancelledException, find_ffmpeg_dir
from core.url_parser import extract_urls_from_text, is_playlist_url


class Handler(SimpleHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def do_GET(self):
        if self.path == '/attachment':
            self.send_response(200)
            self.send_header('Content-Disposition', 'attachment; filename="../../report.pdf"')
            self.send_header('Content-Type', 'application/pdf')
            self.send_header('Content-Length', '7')
            self.end_headers()
            self.wfile.write(b'%PDF-12')
        else:
            super().do_GET()


class WebDownloads(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = tempfile.TemporaryDirectory()
        root = Path(cls.root.name)
        (root / 'page.html').write_text('<html><title>Local video</title><video src="clip.mp4" controls></video></html>')
        (root / 'large.bin').write_bytes(b'X' * 512000)
        subprocess.run([os.path.join(find_ffmpeg_dir(), 'ffmpeg.exe'), '-v', 'error',
            '-f', 'lavfi', '-i', 'color=c=blue:s=160x90:d=0.5', '-f', 'lavfi', '-i',
            'sine=frequency=440:duration=0.5', '-c:v', 'mpeg4', '-c:a', 'aac', '-shortest', str(root / 'clip.mp4')], check=True)
        cls.server = ThreadingHTTPServer(('127.0.0.1', 0), functools.partial(Handler, directory=cls.root.name))
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        cls.base = f'http://127.0.0.1:{cls.server.server_port}'

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join()
        cls.root.cleanup()

    def test_signed_links_are_preserved_and_deduplicated(self):
        url = 'https://example.org/file?token=a,b;c&list=abc'
        self.assertEqual(extract_urls_from_text(url + '\n' + url), [url])
        self.assertFalse(is_playlist_url(url))
        self.assertEqual(extract_urls_from_text('example.org/file'), ['https://example.org/file'])
        self.assertEqual(extract_urls_from_text('file:///C:/Windows/test javascript:alert(1)'), [])

    def test_safe_attachment_and_skip_existing(self):
        with tempfile.TemporaryDirectory() as folder:
            path, exists = download_file(self.base + '/attachment', folder)
            self.assertEqual(os.path.dirname(path), folder)
            self.assertTrue(Path(path).read_bytes().startswith(b'%PDF'))
            self.assertFalse(exists)
            self.assertTrue(download_file(self.base + '/attachment', folder)[1])
            self.assertTrue(safe_filename('CON.txt').startswith('_'))

    def test_html_is_not_saved_as_a_file(self):
        with tempfile.TemporaryDirectory() as folder:
            with self.assertRaisesRegex(ValueError, 'web page'):
                download_file(self.base + '/page.html', folder)
            self.assertEqual(os.listdir(folder), [])

    def test_cancel_does_not_leave_or_replace_files(self):
        event = threading.Event()
        with tempfile.TemporaryDirectory() as folder:
            (Path(folder) / 'unrelated.part').write_bytes(b'keep')
            with self.assertRaises(DownloadCancelledException):
                download_file(self.base + '/large.bin', folder,
                    progress_callback=lambda data: event.set(), cancel_event=event)
            self.assertEqual(os.listdir(folder), ['unrelated.part'])

    def test_generic_page_video_and_audio_with_real_ffmpeg(self):
        engine = AudioDownloader()
        with tempfile.TemporaryDirectory() as folder:
            for profile in ('MP4 · 720p', 'MP3 (192 kbps)'):
                with self.subTest(profile=profile):
                    path = engine.download_media(url=self.base + '/page.html', download_dir=folder,
                        format_label=profile, add_metadata=False, embed_thumbnail=False)
                    self.assertGreater(os.path.getsize(path), 100)
                    result = subprocess.run([os.path.join(find_ffmpeg_dir(), 'ffprobe.exe'), '-v', 'error',
                        '-show_entries', 'format=format_name', '-of', 'csv=p=0', path], capture_output=True, text=True, check=True)
                    self.assertIn('mp4' if profile.startswith('MP4') else 'mp3', result.stdout)


if __name__ == '__main__':
    unittest.main()
