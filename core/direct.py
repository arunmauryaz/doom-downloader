"""Streaming HTTP downloads for original files."""
import mimetypes
import os
import re
import tempfile
import time
from email.message import Message
from urllib.parse import unquote, urlsplit

import requests


def safe_filename(name):
    name = re.sub(r'[<>:"/\\|?*\x00-\x1f]', '_', name).strip(' .')[:180]
    if not name:
        name = 'download'
    if name.split('.')[0].upper() in {'CON', 'PRN', 'AUX', 'NUL', *(f'COM{i}' for i in range(1, 10)), *(f'LPT{i}' for i in range(1, 10))}:
        name = '_' + name
    return name


def download_file(url, download_dir, progress_callback=None, cancel_event=None, skip_existing=True):
    from .downloader import DownloadCancelledException

    def check_cancel():
        if cancel_event and cancel_event.is_set():
            raise DownloadCancelledException('Cancelled')

    check_cancel()
    os.makedirs(download_dir, exist_ok=True)
    temporary = None
    try:
        with requests.get(url, stream=True, timeout=(15, 30), headers={'User-Agent': 'DoomDownloader/1.0', 'Accept-Encoding': 'identity'}) as response:
            response.raise_for_status()
            check_cancel()
            content_type = response.headers.get('Content-Type', '').split(';')[0].lower()
            message = Message()
            message['Content-Disposition'] = response.headers.get('Content-Disposition', '')
            name = message.get_filename()
            if content_type in ('text/html', 'application/xhtml+xml') and not name:
                raise ValueError('This link opens a web page. Use Audio or Video for embedded media, or paste a direct file link.')
            if not name:
                name = unquote(urlsplit(response.url).path.rsplit('/', 1)[-1]) or 'download'
                if not os.path.splitext(name)[1]:
                    name += mimetypes.guess_extension(content_type) or '.bin'
            target = os.path.join(os.path.abspath(download_dir), safe_filename(name))
            if skip_existing and os.path.isfile(target):
                return target, True
            total = int(response.headers.get('Content-Length') or 0) if response.headers.get('Content-Encoding', 'identity') == 'identity' else 0
            received = 0
            started = time.monotonic()
            last_update = 0
            fd, temporary = tempfile.mkstemp(prefix='.doom-', suffix='.part', dir=download_dir)
            with os.fdopen(fd, 'wb') as output:
                for chunk in response.iter_content(chunk_size=128 * 1024):
                    check_cancel()
                    if not chunk:
                        continue
                    output.write(chunk)
                    received += len(chunk)
                    now = time.monotonic()
                    if progress_callback and now - last_update >= 0.15:
                        speed = received / max(now - started, 0.001)
                        progress_callback({'status': 'downloading', 'percent': min(100, received / total * 100) if total else 0,
                            'downloaded_bytes': received, 'total_bytes': total, 'speed': speed,
                            'speed_str': f'{speed / 1024 / 1024:.1f} MB/s',
                            'eta_str': f'{int((total - received) / speed)}s' if total else '--'})
                        last_update = now
            check_cancel()
            if total and received != total:
                raise IOError('Incomplete response. Retry the download.')
            if skip_existing and os.path.isfile(target):
                return target, True
            os.replace(temporary, target)
            temporary = None
            return target, False
    finally:
        if temporary and os.path.isfile(temporary):
            os.remove(temporary)
