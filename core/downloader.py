"""
Downloader engine wrapping yt-dlp with FFmpeg integration.
Embeds album cover artwork directly into audio files (MP3, FLAC, M4A, WAV) so the file itself
displays the thumbnail in Windows Explorer and media players without creating separate image files.
"""

import os
import sys
import shutil
import threading
from typing import Callable, Optional, Dict, Any
import yt_dlp
from mutagen.id3 import ID3
from .formats import get_format_info
from .tagger import fetch_thumbnail_jpeg, embed_artwork

class DownloadCancelledException(Exception):
    """Raised when user cancels the download."""
    pass

def find_ffmpeg_dir() -> Optional[str]:
    """
    Finds the directory containing ffmpeg.exe and ffprobe.exe.
    Checks local project bin folder, WinGet installation, and system PATH.
    """
    current_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(current_dir)
    local_bin = os.path.join(project_root, "bin")
    if os.path.isfile(os.path.join(local_bin, "ffmpeg.exe")):
        return local_bin

    which_ffmpeg = shutil.which("ffmpeg")
    if which_ffmpeg:
        return os.path.dirname(os.path.abspath(which_ffmpeg))

    winget_base = os.path.join(os.path.expanduser("~"), r"AppData\Local\Microsoft\WinGet\Packages")
    if os.path.isdir(winget_base):
        for root, dirs, files in os.walk(winget_base):
            if "ffmpeg.exe" in files:
                return root

    for base in [os.path.expanduser("~"), r"C:\Program Files", r"C:\Program Files (x86)"]:
        candidate = os.path.join(base, "ffmpeg", "bin")
        if os.path.isfile(os.path.join(candidate, "ffmpeg.exe")):
            return candidate

    return None

def get_best_thumbnail_url(info: Dict[str, Any]) -> str:
    """Extracts highest resolution thumbnail URL from yt-dlp info dictionary."""
    thumbnails = info.get("thumbnails", [])
    if thumbnails:
        valid = [t for t in thumbnails if t.get("url")]
        if valid:
            valid.sort(key=lambda t: (t.get("width") or 0) * (t.get("height") or 0), reverse=True)
            return valid[0]["url"]
    return info.get("thumbnail", "")

def normalize_title(s: str) -> str:
    """Removes punctuation and non-alphanumeric chars for robust title matching."""
    import re
    return re.sub(r'[\W_]+', '', s).lower()

def find_existing_song(download_dir: str, title: str, ext: str) -> Optional[str]:
    """
    Checks if a song with this title and format already exists in download_dir.
    Returns the absolute path to the existing file if found, otherwise None.
    """
    if not os.path.isdir(download_dir) or not title:
        return None

    # 1. Exact path check
    exact_path = os.path.join(download_dir, f"{title}.{ext}")
    if os.path.isfile(exact_path) and os.path.getsize(exact_path) > 10240:
        return exact_path

    # 2. yt-dlp sanitized filename check
    try:
        with yt_dlp.YoutubeDL({'outtmpl': os.path.join(download_dir, '%(title)s.%(ext)s'), 'quiet': True}) as ydl:
            expected = ydl.prepare_filename({'title': title, 'ext': ext})
            if os.path.isfile(expected) and os.path.getsize(expected) > 10240:
                return expected
    except Exception:
        pass

    # 3. Normalized title match in the folder
    target_norm = normalize_title(title)
    if target_norm:
        try:
            for f in os.listdir(download_dir):
                if f.lower().endswith(f".{ext.lower()}"):
                    base = os.path.splitext(f)[0]
                    if normalize_title(base) == target_norm:
                        candidate = os.path.join(download_dir, f)
                        if os.path.isfile(candidate) and os.path.getsize(candidate) > 10240:
                            return candidate
        except Exception:
            pass

    return None

class AudioDownloader:
    def __init__(self, ffmpeg_dir: Optional[str] = None):
        self.ffmpeg_dir = ffmpeg_dir or find_ffmpeg_dir()
        if self.ffmpeg_dir:
            os.environ["PATH"] = self.ffmpeg_dir + os.pathsep + os.environ.get("PATH", "")

    def is_ffmpeg_available(self) -> bool:
        if not self.ffmpeg_dir:
            return False
        return os.path.isfile(os.path.join(self.ffmpeg_dir, "ffmpeg.exe"))

    def fetch_video_info(self, url: str) -> Dict[str, Any]:
        """Fetches title, duration, best thumbnail, and uploader for a single video."""
        opts = {
            'noplaylist': True,
            'skip_download': True,
            'quiet': True,
            'no_warnings': True,
            'ignoreerrors': False,
            'socket_timeout': 20,
            'retries': 2,
        }
        if self.ffmpeg_dir:
            opts['ffmpeg_location'] = self.ffmpeg_dir

        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(url, download=False)
            if not info:
                raise RuntimeError('No media found at this link.')
            if info.get('_type') == 'playlist':
                raise RuntimeError('This page contains a collection. Enable Collections or use a media link.')
            best_thumb = get_best_thumbnail_url(info)
            return {
                'id': info.get('id', ''),
                'title': info.get('title', 'Unknown Title'),
                'uploader': info.get('uploader') or info.get('channel', 'Unknown Artist'),
                'duration': info.get('duration', 0),
                'thumbnail': best_thumb,
                'webpage_url': info.get('webpage_url', url)
            }

    def download_media(self, **kwargs) -> str:
        if get_format_info(kwargs["format_label"]).get("kind") == "video":
            return self.download_video(**kwargs)
        return self.download_audio(**kwargs)

    def download_video(self, url, download_dir, format_label, add_metadata=True,
                       progress_callback=None, cancel_event=None, **kwargs):
        if not self.is_ffmpeg_available():
            raise RuntimeError("FFmpeg is required for video merging. Place it in bin/.")
        fmt = get_format_info(format_label)
        ext, height = fmt["ext"], fmt["height"]
        cap = f"[height<=?{height}]" if height else ""
        if ext == "mp4":
            selector = f"bv{cap}[ext=mp4]+ba[ext=m4a]/b{cap}[ext=mp4]"
        elif ext == "webm":
            selector = f"bv{cap}[ext=webm]+ba[ext=webm]/b{cap}[ext=webm]"
        else:
            selector = f"bv{cap}+ba/b{cap}"
        final_paths = []

        def check_cancel():
            if cancel_event and cancel_event.is_set():
                raise DownloadCancelledException("Download cancelled by user")

        def progress(data):
            check_cancel()
            if not progress_callback:
                return
            total = data.get("total_bytes") or data.get("total_bytes_estimate") or 0
            if data["status"] == "downloading":
                progress_callback({"status": "downloading",
                    "percent": min(100, data.get("downloaded_bytes", 0) / total * 100) if total else 0,
                    "speed": data.get("speed") or 0, "speed_str": data.get("_speed_str", "--"),
                    "eta_str": data.get("_eta_str", "--"), "total_bytes": total,
                    "downloaded_bytes": data.get("downloaded_bytes", 0)})
            elif data["status"] == "finished":
                progress_callback({"status": "converting", "message": "Merging video and audio…"})

        def postprocess(data):
            check_cancel()
            path = data.get("info_dict", {}).get("filepath")
            if path:
                final_paths.append(path)

        processors = [{"key": "FFmpegVideoRemuxer", "preferedformat": ext}]
        if add_metadata:
            processors.append({"key": "FFmpegMetadata", "add_metadata": True})
        opts = {"format": selector, "merge_output_format": ext,
                "outtmpl": os.path.join(download_dir, "%(title)s [%(id)s].%(ext)s"),
                "postprocessors": processors, "progress_hooks": [progress],
                "postprocessor_hooks": [postprocess], "ffmpeg_location": self.ffmpeg_dir,
                "noplaylist": True, "overwrites": True, "quiet": True, "retries": 3, "socket_timeout": 30}
        os.makedirs(download_dir, exist_ok=True)
        check_cancel()
        try:
            with yt_dlp.YoutubeDL(opts) as ydl:
                info = ydl.extract_info(url, download=True)
                check_cancel()
                if not info:
                    raise RuntimeError("No video stream was returned.")
                expected = os.path.splitext(ydl.prepare_filename(info))[0] + "." + ext
                paths = [expected] + list(reversed(final_paths))
                for path in paths:
                    if path.endswith("." + ext) and os.path.isfile(path):
                        return os.path.abspath(path)
                raise RuntimeError("Video processing finished without an output file.")
        except Exception:
            check_cancel()
            raise

    def download_audio(
        self,
        url: str,
        download_dir: str,
        format_label: str,
        embed_thumbnail: bool = True,
        add_metadata: bool = True,
        crop_square: bool = True,
        progress_callback: Optional[Callable[[Dict[str, Any]], None]] = None,
        cancel_event: Optional[threading.Event] = None,
        custom_title: Optional[str] = None,
        custom_artist: Optional[str] = None,
        custom_thumbnail_url: Optional[str] = None
    ) -> str:
        """
        Downloads audio and embeds the thumbnail artwork directly into the file.
        Leaves NO separate image files in the directory.
        """
        fmt_info = get_format_info(format_label)
        codec = fmt_info["codec"]
        quality = fmt_info["quality"]
        ext = fmt_info["ext"]

        os.makedirs(download_dir, exist_ok=True)
        final_filepath = None

        def progress_hook(d):
            nonlocal final_filepath
            if cancel_event and cancel_event.is_set():
                raise DownloadCancelledException("Download cancelled by user")

            status = d.get('status')
            if status == 'downloading':
                total = d.get('total_bytes') or d.get('total_bytes_estimate') or 0
                downloaded = d.get('downloaded_bytes', 0)
                speed = d.get('speed') or 0
                eta = d.get('eta') or 0

                percent = 0.0
                if total > 0:
                    percent = round((downloaded / total) * 100, 1)

                if progress_callback:
                    progress_callback({
                        'status': 'downloading',
                        'percent': percent,
                        'downloaded_bytes': downloaded,
                        'total_bytes': total,
                        'speed': speed,
                        'speed_str': d.get('_speed_str', 'N/A'),
                        'eta': eta,
                        'eta_str': d.get('_eta_str', 'N/A'),
                        'filename': d.get('filename')
                    })

            elif status == 'finished':
                final_filepath = d.get('filename')
                if progress_callback:
                    progress_callback({
                        'status': 'converting',
                        'message': f"Extracting audio to {ext.upper()}...",
                        'percent': 100.0
                    })

        def postprocessor_hook(d):
            if cancel_event and cancel_event.is_set():
                raise DownloadCancelledException("Download cancelled during conversion")

            postprocessor = d.get('postprocessor', '')
            status = d.get('status', '')

            if progress_callback and status == 'started':
                if 'ExtractAudio' in postprocessor:
                    progress_callback({
                        'status': 'converting',
                        'message': f"Converting audio to {ext.upper()}...",
                        'percent': 100.0
                    })
                elif 'EmbedThumbnail' in postprocessor:
                    progress_callback({
                        'status': 'converting',
                        'message': "Embedding album cover art into song file...",
                        'percent': 100.0
                    })

        # Base postprocessors
        postprocessors = [
            {
                'key': 'FFmpegExtractAudio',
                'preferredcodec': codec,
                'preferredquality': quality,
                'nopostoverwrites': False,
            }
        ]

        # For formats supported by yt-dlp EmbedThumbnail (mp3, m4a, flac, opus)
        if embed_thumbnail and codec in ['mp3', 'm4a', 'flac', 'opus', 'ogg']:
            postprocessors.append({'key': 'FFmpegThumbnailsConvertor', 'format': 'jpg'})
            if add_metadata:
                postprocessors.append({'key': 'FFmpegMetadata', 'add_metadata': True})
            postprocessors.append({'key': 'EmbedThumbnail', 'already_have_thumbnail': False})
        elif add_metadata and fmt_info.get("supports_metadata", True):
            postprocessors.append({'key': 'FFmpegMetadata', 'add_metadata': True})

        ydl_opts = {
            'format': 'bestaudio/best',
            'outtmpl': os.path.join(download_dir, '%(title)s.%(ext)s'),
            'postprocessors': postprocessors,
            'writethumbnail': embed_thumbnail and codec in ['mp3', 'm4a', 'flac', 'opus', 'ogg'],
            'progress_hooks': [progress_hook],
            'postprocessor_hooks': [postprocessor_hook],
            'quiet': True,
            'no_warnings': True,
            'noplaylist': True,
            'overwrites': True,
            'retries': 3,
            'socket_timeout': 30,
            'ignoreerrors': False,
        }

        if self.ffmpeg_dir:
            ydl_opts['ffmpeg_location'] = self.ffmpeg_dir

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                if not info:
                    raise Exception("Failed to retrieve audio stream from YouTube")

                expected_path = os.path.splitext(ydl.prepare_filename(info))[0] + f".{ext}"
                final_filepath = expected_path
                if not os.path.isfile(final_filepath):
                    raise RuntimeError("Audio processing finished without an output file.")

                # Clean rename if custom_title provided (e.g. from Spotify)
                if custom_title and final_filepath and os.path.isfile(final_filepath):
                    clean_name = f"{custom_artist} - {custom_title}" if custom_artist and custom_artist != "YouTube" else custom_title
                    import re
                    clean_name = re.sub(r'[\\/*?:"<>|]', "", clean_name).strip()
                    target_filepath = os.path.join(download_dir, f"{clean_name}.{ext}")
                    if target_filepath != final_filepath:
                        try:
                            if os.path.isfile(target_filepath):
                                os.remove(target_filepath)
                            os.rename(final_filepath, target_filepath)
                            final_filepath = target_filepath
                        except Exception as e:
                            print(f"[Doom Downloader] Rename warning: {e}")

                # ---------------- Guarantee ID3v2.3 & Thumbnail Embedding ----------------
                if embed_thumbnail and final_filepath and os.path.isfile(final_filepath):
                    best_thumb_url = custom_thumbnail_url or get_best_thumbnail_url(info)
                    meta_title = custom_title or info.get("title", "")
                    meta_artist = custom_artist or info.get("uploader") or info.get("channel", "")

                    # MP3: Ensure ID3v2.3 for Windows Explorer native thumbnail display
                    if ext == "mp3":
                        try:
                            audio = ID3(final_filepath)
                            has_apic = any('APIC' in k for k in audio.keys())
                            if (not has_apic or custom_thumbnail_url) and best_thumb_url:
                                thumb_data = fetch_thumbnail_jpeg(best_thumb_url, square_crop=crop_square)
                                if thumb_data:
                                    embed_artwork(
                                        final_filepath,
                                        thumb_data[0],
                                        metadata={
                                            "title": meta_title,
                                            "uploader": meta_artist
                                        }
                                    )
                            else:
                                # Resave with v2_version=3 (Critical for Windows Explorer!)
                                audio.save(final_filepath, v2_version=3)
                        except Exception as e:
                            print(f"[Doom Downloader] ID3 check warning: {e}")

                    # WAV: Embed artwork into ID3 chunk
                    elif ext == "wav" and best_thumb_url:
                        thumb_data = fetch_thumbnail_jpeg(best_thumb_url, square_crop=crop_square)
                        if thumb_data:
                            embed_artwork(
                                final_filepath,
                                thumb_data[0],
                                metadata={
                                    "title": meta_title,
                                    "uploader": meta_artist
                                }
                            )

                    # FLAC, M4A, OPUS with custom metadata or thumbnail
                    elif ext in ["flac", "m4a", "opus", "ogg"] and (custom_title or custom_thumbnail_url):
                        if best_thumb_url:
                            thumb_data = fetch_thumbnail_jpeg(best_thumb_url, square_crop=crop_square)
                            if thumb_data:
                                embed_artwork(
                                    final_filepath,
                                    thumb_data[0],
                                    metadata={
                                        "title": meta_title,
                                        "uploader": meta_artist
                                    }
                                )

                # ---------------- Clean up ANY Separate Images ----------------
                self._cleanup_separate_images(download_dir, final_filepath)

                if progress_callback:
                    progress_callback({
                        'status': 'completed',
                        'percent': 100.0,
                        'filepath': final_filepath
                    })

                return final_filepath

        except DownloadCancelledException:
            # Preserve partial files for resuming; never delete other workers' files.
            raise
        except Exception as e:
            # Preserve partial files for resuming; never delete other workers' files.
            raise e

    def _cleanup_separate_images(self, download_dir: str, audio_filepath: Optional[str]):
        """
        Removes any leftover thumbnail files (.jpg, .jpeg, .webp, .png, .part) so that
        ONLY the audio file remains in the folder.
        """
        try:
            if not audio_filepath or not os.path.isfile(audio_filepath):
                return
            base_name = os.path.splitext(os.path.basename(audio_filepath))[0]
            for ext in [".jpg", ".jpeg", ".webp", ".png", ".part", ".ytdl", ".temp"]:
                candidate = os.path.join(download_dir, f"{base_name}{ext}")
                if os.path.isfile(candidate):
                    try:
                        os.remove(candidate)
                    except Exception:
                        pass
        except Exception:
            pass
