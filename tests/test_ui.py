"""Widget-level checks for input modes, queue views and library navigation."""
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch

from core.config import config
from core.downloader import AudioDownloader
from core.queue_manager import QueueManager, QueueItemStatus
from gui.app import DownloaderApp


class InterfaceTests(unittest.TestCase):
    def setUp(self):
        self.save = patch.object(config, 'save')
        self.save.start()
        self.settings = config.settings.copy()
        self.engine = AudioDownloader()
        self.manager = QueueManager(self.engine)
        self.manager.pause()
        self.app = DownloaderApp(self.engine, self.manager)
        self.app.update()

    def tearDown(self):
        for timer in self.app.tk.splitlist(self.app.tk.call("after", "info")):
            self.app.tk.call("after", "cancel", timer)
        self.app._on_closing()
        config.settings = self.settings
        self.save.stop()

    def test_auto_bulk_and_newline_shortcut(self):
        app = self.app
        app.url_textbox.insert('1.0', 'https://example.org/a\nhttps://example.org/b')
        app._input_changed()
        self.assertEqual(app.input_switch.get(), 'Bulk')
        app._clear_input()
        self.assertEqual(app.input_switch.get(), 'Single')
        app.url_textbox.insert('1.0', 'https://example.org/a')
        self.assertEqual(app._bulk_newline(), 'break')
        self.assertEqual(app.input_mode, 'Bulk')
        self.assertIn('\n', app.url_textbox.get('1.0', 'end-1c'))

    def test_modes_library_and_minimum_layout(self):
        app = self.app
        app.geometry('960x760')
        for mode in ('Video', 'File', 'Audio'):
            app._on_mode_changed(mode)
            app.update()
            self.assertEqual(app.cb_artwork.cget('state'), 'normal' if mode == 'Audio' else 'disabled')
            self.assertTrue(app.download_btn.winfo_ismapped())
        app._toggle_library()
        app.update()
        self.assertTrue(app.library_panel.winfo_ismapped())
        self.assertGreaterEqual(app.main_frame.winfo_width(), 900)
        app._toggle_library()
        app.update()
        self.assertFalse(app.library_panel.winfo_ismapped())
        app._set_input_mode('Bulk')
        app.update()
        self.assertGreater(app.scroll_frame.winfo_height(), 70)

    def test_library_lists_and_filters_files(self):
        app = self.app
        with tempfile.TemporaryDirectory() as directory:
            (Path(directory) / 'saved.pdf').write_bytes(b'PDF')
            (Path(directory) / 'album').mkdir()
            app._navigate_library(directory)
            for _ in range(50):
                app._drain_events()
                app.update()
                if len(app._library_entries) == 2:
                    break
                time.sleep(0.01)
            self.assertEqual([entry[0] for entry in app._library_entries], ['album', 'saved.pdf'])
            app.library_search.insert(0, 'saved')
            app._filter_library()
            self.assertEqual(len(app.library_list.winfo_children()), 1)

    def test_enqueue_generic_and_file_urls(self):
        app = self.app
        app._on_mode_changed('File')
        app._process_input_urls(['https://example.org/report.pdf'], dict(detect_playlist=False,
            skip_existing=True, current_fmt='Original file', target_dir='.', artwork=False, metadata=False))
        app._drain_events()
        app.update()
        self.assertEqual(self.manager.items[0].format_label, 'Original file')
        self.assertEqual(self.manager.items[0].status, QueueItemStatus.QUEUED)
        self.assertEqual(len(app.card_widgets), 1)
        app._on_filter_changed('Failed')
        self.assertFalse(next(iter(app.card_widgets.values())).winfo_ismapped())


if __name__ == '__main__':
    unittest.main()
