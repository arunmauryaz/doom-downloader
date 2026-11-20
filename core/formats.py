"""
Format definitions and presets for audio, video, and direct file downloads.
"""

from typing import Optional

AUDIO_FORMATS = {
    "MP3 (320 kbps)": {
        "codec": "mp3",
        "ext": "mp3",
        "quality": "320",
        "badge": "MP3",
        "supports_thumbnail": True,
        "supports_metadata": True,
    },
    "WAV (Lossless PCM)": {
        "codec": "wav",
        "ext": "wav",
        "quality": "0",
        "badge": "WAV",
        "supports_thumbnail": True,
        "supports_metadata": True,
    },
    "FLAC (Lossless)": {
        "codec": "flac",
        "ext": "flac",
        "quality": "0",
        "badge": "FLAC",
        "supports_thumbnail": True,
        "supports_metadata": True,
    },
    "M4A (AAC)": {
        "codec": "m4a",
        "ext": "m4a",
        "quality": "0",
        "badge": "M4A",
        "supports_thumbnail": True,
        "supports_metadata": True,
    },
    "MP3 (192 kbps)": {
        "codec": "mp3",
        "ext": "mp3",
        "quality": "192",
        "badge": "MP3",
        "supports_thumbnail": True,
        "supports_metadata": True,
    },
    "OPUS": {
        "codec": "opus",
        "ext": "opus",
        "quality": "0",
        "badge": "OPUS",
        "supports_thumbnail": True,
        "supports_metadata": True,
    },
    "OGG (Vorbis)": {
        "codec": "vorbis",
        "ext": "ogg",
        "quality": "5",
        "badge": "OGG",
        "supports_thumbnail": False,
        "supports_metadata": True,
    }
}

VIDEO_FORMATS = {
    f"{container.upper()} · {label}": {
        "kind": "video", "ext": container, "badge": container.upper(),
        "height": height, "supports_thumbnail": False, "supports_metadata": True,
    }
    for container in ("mp4", "mkv", "webm")
    for label, height in (("Best available", None), ("2160p", 2160), ("1440p", 1440), ("1080p", 1080), ("720p", 720), ("480p", 480), ("360p", 360))
}

FORMAT_NAMES = list(AUDIO_FORMATS)
VIDEO_FORMAT_NAMES = list(VIDEO_FORMATS)
FILE_FORMAT = "Original file"
FILE_FORMATS = {FILE_FORMAT: {"kind": "file", "ext": "", "badge": "FILE", "supports_thumbnail": False, "supports_metadata": False}}
DEFAULT_FORMAT = "MP3 (320 kbps)"


def get_format_info(format_label: str) -> dict:
    if format_label and format_label.startswith("[Audio] "):
        format_label = format_label.replace("[Audio] ", "", 1)
    all_formats = {**AUDIO_FORMATS, **VIDEO_FORMATS, **FILE_FORMATS}
    if format_label in all_formats:
        return all_formats[format_label]
    resolved = resolve_format_alias(format_label)
    if resolved and resolved.startswith("[Audio] "):
        resolved = resolved.replace("[Audio] ", "", 1)
    return all_formats.get(resolved, AUDIO_FORMATS[DEFAULT_FORMAT])


def resolve_format_alias(
    alias: Optional[str] = None,
    media_type: str = "video",
    audio_only: bool = False
) -> str:
    """
    Intelligently maps short user-friendly CLI aliases (e.g. '1080p', 'mp3', 'wav', 'best', '4k')
    or exact labels to a supported format label in AUDIO_FORMATS, VIDEO_FORMATS, or FILE_FORMATS.
    """
    if not alias:
        if audio_only:
            return f"[Audio] {DEFAULT_FORMAT}" if media_type == "video" else DEFAULT_FORMAT
        if media_type == "direct_file":
            return FILE_FORMAT
        if media_type in ("spotify_audio", "audio"):
            return DEFAULT_FORMAT
        return "MP4 · Best available"

    raw = alias.strip()
    is_explicit_audio = audio_only
    if raw.lower().startswith("[audio] "):
        is_explicit_audio = True
        raw = raw[8:].strip()

    # Exact key matches
    if raw in AUDIO_FORMATS:
        return f"[Audio] {raw}" if (media_type == "video" or is_explicit_audio) else raw
    if raw in VIDEO_FORMATS:
        return f"[Audio] {DEFAULT_FORMAT}" if is_explicit_audio else raw
    if raw in FILE_FORMATS:
        return raw

    # Case-insensitive direct matches
    low = raw.lower()
    for k in AUDIO_FORMATS:
        if k.lower() == low:
            return f"[Audio] {k}" if (media_type == "video" or is_explicit_audio) else k
    for k in VIDEO_FORMATS:
        if k.lower() == low:
            return f"[Audio] {DEFAULT_FORMAT}" if is_explicit_audio else k

    # Direct file aliases
    if low in ("file", "raw", "original", "direct", "original file"):
        return FILE_FORMAT

    # Audio shortcuts
    audio_map = {
        "mp3": "MP3 (320 kbps)",
        "320": "MP3 (320 kbps)",
        "320k": "MP3 (320 kbps)",
        "320kbps": "MP3 (320 kbps)",
        "192": "MP3 (192 kbps)",
        "192k": "MP3 (192 kbps)",
        "192kbps": "MP3 (192 kbps)",
        "wav": "WAV (Lossless PCM)",
        "pcm": "WAV (Lossless PCM)",
        "flac": "FLAC (Lossless)",
        "lossless": "FLAC (Lossless)",
        "m4a": "M4A (AAC)",
        "aac": "M4A (AAC)",
        "opus": "OPUS",
        "ogg": "OGG (Vorbis)",
        "vorbis": "OGG (Vorbis)",
    }
    if low in audio_map:
        target = audio_map[low]
        return f"[Audio] {target}" if (media_type == "video" or is_explicit_audio) else target

    # Video container selection
    container = "MP4"
    if "mkv" in low:
        container = "MKV"
    elif "webm" in low:
        container = "WEBM"

    # Video height / quality shortcuts
    if any(q in low for q in ("4k", "2160", "2160p", "uhd")):
        return f"[Audio] {DEFAULT_FORMAT}" if is_explicit_audio else f"{container} · 2160p"
    if any(q in low for q in ("1440", "1440p", "2k", "qhd")):
        return f"[Audio] {DEFAULT_FORMAT}" if is_explicit_audio else f"{container} · 1440p"
    if any(q in low for q in ("1080", "1080p", "fhd", "fullhd")):
        return f"[Audio] {DEFAULT_FORMAT}" if is_explicit_audio else f"{container} · 1080p"
    if any(q in low for q in ("720", "720p", "hd")):
        return f"[Audio] {DEFAULT_FORMAT}" if is_explicit_audio else f"{container} · 720p"
    if any(q in low for q in ("480", "480p", "sd")):
        return f"[Audio] {DEFAULT_FORMAT}" if is_explicit_audio else f"{container} · 480p"
    if any(q in low for q in ("best", "max", "highest", "top", "video")):
        return f"[Audio] {DEFAULT_FORMAT}" if is_explicit_audio else f"{container} · Best available"

    # Fallback based on type
    if is_explicit_audio:
        return f"[Audio] {DEFAULT_FORMAT}"
    if media_type == "video":
        return f"{container} · Best available"
    if media_type in ("spotify_audio", "audio"):
        return DEFAULT_FORMAT
    if media_type == "direct_file":
        return FILE_FORMAT

    return "MP4 · Best available"

