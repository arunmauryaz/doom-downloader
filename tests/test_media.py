import os
import tempfile
import threading
import unittest
from unittest.mock import patch

from core.downloader import AudioDownloader, DownloadCancelledException
from core.formats import VIDEO_FORMATS
from core.queue_manager import DownloadItem


class FakeYDL:
    options = None

    def __init__(self, options):
        FakeYDL.options = options
        self.options = options

    def __enter__(self):
        return self

    def __exit__(self, *args):
        pass

    def prepare_filename(self, info):
        return self.options['outtmpl'].replace('%(title)s', 'Example').replace('%(id)s', 'abc').replace('%(ext)s', 'webm')

    def extract_info(self, url, download):
        info = {'title': 'Example', 'id': 'abc', 'ext': 'webm'}
        ext = self.options.get('merge_output_format', 'mp3')
        path = os.path.splitext(self.prepare_filename(info))[0] + '.' + ext
        with open(path, 'wb') as output:
            output.write(b'output')
        return info


class MediaTests(unittest.TestCase):
    @patch('core.downloader.yt_dlp.YoutubeDL', FakeYDL)
    def test_every_video_profile_has_bounded_selector_and_correct_output(self):
        engine = AudioDownloader()
        with tempfile.TemporaryDirectory() as folder:
            for label, fmt in VIDEO_FORMATS.items():
                with self.subTest(label=label):
                    result = engine.download_media(url='https://youtube.com/watch?v=example',
                        download_dir=folder, format_label=label, add_metadata=False)
                    self.assertTrue(os.path.isfile(result))
                    self.assertTrue(result.endswith('.' + fmt['ext']))
                    self.assertTrue(FakeYDL.options['noplaylist'])
                    self.assertEqual(len(FakeYDL.options['postprocessors']), 1)
                    if fmt['height']:
                        self.assertIn(f"height<=?{fmt['height']}", FakeYDL.options['format'])

    @patch('core.downloader.yt_dlp.YoutubeDL', FakeYDL)
    def test_audio_path_does_not_pick_another_workers_file(self):
        engine = AudioDownloader()
        with tempfile.TemporaryDirectory() as folder:
            unrelated = os.path.join(folder, 'unrelated.mp3')
            with open(unrelated, 'wb') as output:
                output.write(b'existing')
            result = engine.download_media(url='example', download_dir=folder,
                format_label='MP3 (320 kbps)', embed_thumbnail=False, add_metadata=False)
            self.assertEqual(os.path.basename(result), 'Example.mp3')
            with open(unrelated, 'rb') as existing:
                self.assertEqual(existing.read(), b'existing')

    def test_pre_cancelled_video_does_not_start(self):
        event = threading.Event()
        event.set()
        with tempfile.TemporaryDirectory() as folder:
            with self.assertRaises(DownloadCancelledException):
                AudioDownloader().download_video('example', folder, 'MP4 · 1080p', cancel_event=event)

    def test_duplicate_setting_belongs_to_item(self):
        item = DownloadItem('example', 'MP3 (320 kbps)', '.', skip_existing=False)
        self.assertFalse(item.skip_existing)


if __name__ == '__main__':
    unittest.main()
