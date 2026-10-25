"""
Supported audio formats configuration.
Clean, minimalistic definitions without marketing copy.
"""

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
    }
}

VIDEO_FORMATS = {
    f"{container.upper()} · {label}": {
        "kind": "video", "ext": container, "badge": container.upper(),
        "height": height, "supports_thumbnail": False, "supports_metadata": True,
    }
    for container in ("mp4", "mkv", "webm")
    for label, height in (("Best available", None), ("2160p", 2160), ("1440p", 1440), ("1080p", 1080), ("720p", 720), ("480p", 480))
}
AUDIO_FORMATS["OGG (Vorbis)"] = {
    "codec": "vorbis", "ext": "ogg", "quality": "5", "badge": "OGG",
    "supports_thumbnail": False, "supports_metadata": True,
}
FORMAT_NAMES = list(AUDIO_FORMATS)
VIDEO_FORMAT_NAMES = list(VIDEO_FORMATS)
FILE_FORMAT = "Original file"
FILE_FORMATS = {FILE_FORMAT: {"kind": "file", "ext": "", "badge": "FILE", "supports_thumbnail": False, "supports_metadata": False}}
DEFAULT_FORMAT = "MP3 (320 kbps)"


def get_format_info(format_label: str) -> dict:
    return {**AUDIO_FORMATS, **VIDEO_FORMATS, **FILE_FORMATS}.get(format_label, AUDIO_FORMATS[DEFAULT_FORMAT])
