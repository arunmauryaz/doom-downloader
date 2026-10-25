"""
Audio tagging and album artwork embedding engine.
Supports embedding high-resolution JPEG cover art into MP3, WAV, FLAC, M4A, and OPUS.
Ensures universal cover display in Windows Media Player, Groove, VLC, iTunes, Apple Music, and mobile players.
"""

import os
import io
import base64
import requests
from typing import Optional, Tuple, Dict, Any
from PIL import Image

import mutagen
from mutagen.mp3 import MP3
from mutagen.id3 import ID3, APIC, TIT2, TPE1, TALB, TDRC, ID3NoHeaderError
from mutagen.wave import WAVE
from mutagen.flac import FLAC, Picture
from mutagen.mp4 import MP4, MP4Cover
from mutagen.oggopus import OggOpus

def process_image_to_jpeg_bytes(
    raw_bytes: bytes,
    square_crop: bool = True,
    target_size: int = 1000
) -> Tuple[bytes, Image.Image]:
    """
    Decodes image bytes (WebP, PNG, JPEG), converts to baseline RGB,
    optionally center-crops to square for standard album cover format,
    and returns (jpeg_bytes, pil_image).
    """
    img = Image.open(io.BytesIO(raw_bytes)).convert("RGB")
    width, height = img.size

    if square_crop and width != height:
        # Center-crop to 1:1 aspect ratio
        min_dim = min(width, height)
        left = (width - min_dim) // 2
        top = (height - min_dim) // 2
        right = left + min_dim
        bottom = top + min_dim
        img = img.crop((left, top, right, bottom))

    # Resize if very large
    if img.size[0] > target_size or img.size[1] > target_size:
        img = img.resize((target_size, target_size), Image.Resampling.LANCZOS)

    out_buf = io.BytesIO()
    img.save(out_buf, format="JPEG", quality=95, optimize=True)
    jpeg_bytes = out_buf.getvalue()
    return jpeg_bytes, img

def fetch_thumbnail_jpeg(
    thumbnail_url: str,
    square_crop: bool = True
) -> Optional[Tuple[bytes, Image.Image]]:
    """Downloads thumbnail from URL and processes into standard JPEG cover bytes."""
    if not thumbnail_url:
        return None
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }
        resp = requests.get(thumbnail_url, headers=headers, timeout=12)
        if resp.status_code == 200 and resp.content:
            return process_image_to_jpeg_bytes(resp.content, square_crop=square_crop)
    except Exception as e:
        print(f"[Tagger] Error fetching thumbnail from {thumbnail_url}: {e}")
    return None

def embed_artwork(
    audio_path: str,
    image_bytes: bytes,
    metadata: Optional[Dict[str, Any]] = None
) -> bool:
    """
    Embeds the provided JPEG artwork bytes directly into the audio file container.
    Supports MP3 (ID3v2.3), WAV (RIFF ID3), FLAC (Picture), M4A (covr), OPUS.
    No separate image file is ever created.
    """
    if not os.path.isfile(audio_path) or not image_bytes:
        return False

    ext = os.path.splitext(audio_path)[1].lower().lstrip(".")
    meta = metadata or {}
    title = meta.get("title", "")
    artist = meta.get("uploader", "") or meta.get("artist", "")
    album = meta.get("album", "") or title

    try:
        # 1. MP3 Format (Forces ID3v2.3 for Windows Explorer native thumbnail display)
        if ext == "mp3":
            try:
                audio = ID3(audio_path)
            except ID3NoHeaderError:
                audio = ID3()

            # Remove previous APIC frames
            audio.delall("APIC")
            audio.add(APIC(
                encoding=3,  # UTF-8
                mime="image/jpeg",
                type=3,      # Cover (front)
                desc="Cover",
                data=image_bytes
            ))
            if title:
                audio.add(TIT2(encoding=3, text=title))
            if artist:
                audio.add(TPE1(encoding=3, text=artist))
            if album:
                audio.add(TALB(encoding=3, text=album))

            # Critical: v2_version=3 is what Windows Explorer shell requires to show the thumbnail on the file!
            audio.save(audio_path, v2_version=3)
            return True

        # 2. WAV Format (RIFF with ID3 chunk)
        elif ext == "wav":
            audio = WAVE(audio_path)
            if audio.tags is None:
                audio.add_tags()
            audio.tags.delall("APIC")
            audio.tags.add(APIC(
                encoding=3,
                mime="image/jpeg",
                type=3,
                desc="Cover",
                data=image_bytes
            ))
            if title:
                audio.tags.add(TIT2(encoding=3, text=title))
            if artist:
                audio.tags.add(TPE1(encoding=3, text=artist))
            if album:
                audio.tags.add(TALB(encoding=3, text=album))

            audio.save()
            return True

        # 3. FLAC Format
        elif ext == "flac":
            audio = FLAC(audio_path)
            picture = Picture()
            picture.type = 3  # Cover (front)
            picture.mime = "image/jpeg"
            picture.desc = "Cover"
            picture.data = image_bytes
            audio.clear_pictures()
            audio.add_picture(picture)
            if title:
                audio["title"] = title
            if artist:
                audio["artist"] = artist
            if album:
                audio["album"] = album
            audio.save()
            return True

        # 4. M4A / AAC Format
        elif ext in ["m4a", "mp4", "aac"]:
            audio = MP4(audio_path)
            audio["covr"] = [MP4Cover(image_bytes, imageformat=MP4Cover.FORMAT_JPEG)]
            if title:
                audio["\xa9nam"] = title
            if artist:
                audio["\xa9ART"] = artist
            if album:
                audio["\xa9alb"] = album
            audio.save()
            return True

        # 5. OPUS / OGG Format
        elif ext in ["opus", "ogg"]:
            audio = OggOpus(audio_path)
            picture = Picture()
            picture.type = 3
            picture.mime = "image/jpeg"
            picture.desc = "Cover"
            picture.data = image_bytes
            encoded_picture = base64.b64encode(picture.write()).decode("ascii")
            audio["metadata_block_picture"] = [encoded_picture]
            if title:
                audio["title"] = title
            if artist:
                audio["artist"] = artist
            if album:
                audio["album"] = album
            audio.save()
            return True

    except Exception as e:
        print(f"[Tagger] Warning: Failed to embed cover art into {audio_path}: {e}")
        return False

    return False
