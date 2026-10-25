"""
URL parsing and extraction module for Doom Downloader.
Supports single video links and user-created YouTube playlists.
Strictly ignores default/algorithmic YouTube Mixes (RD...).
"""

import re
import urllib.parse
from typing import List, Dict, Any, Tuple, Optional
import yt_dlp
from .spotify import (
    is_spotify_url, is_spotify_playlist_or_album,
    is_spotify_track, fetch_spotify_track, fetch_spotify_collection
)

# Regex patterns for YouTube URLs
YT_VIDEO_REGEX = re.compile(
    r'(https?://)?(www\.|m\.|music\.)?(youtube\.com/(watch\?v=|embed/|v/|shorts/)|youtu\.be/)([\w\-]{11})',
    re.IGNORECASE
)

# Playlist matching (e.g. list=PL..., list=OLAK..., list=UU..., etc.)
YT_PLAYLIST_PARAM_REGEX = re.compile(
    r'[?&]list=([a-zA-Z0-9_\-]+)',
    re.IGNORECASE
)

def extract_urls_from_text(text: str) -> List[str]:
    """Accept HTTP(S) links without damaging signed query strings."""
    urls = []
    text = re.sub(r"[,;](?=https?://)", " ", text, flags=re.I)
    for token in re.split(r"\s+", text.strip()):
        token = token.strip("\"'<>")
        if token.startswith("spotify:"):
            if is_spotify_url(token):
                urls.append(token)
            continue
        if not re.match(r"https?://", token, re.I):
            if re.match(r"(?:[a-zA-Z0-9-]+\.)+[a-zA-Z]{2,}(?::\d+)?(?:/|$)", token):
                token = "https://" + token
            else:
                continue
        try:
            parsed = urllib.parse.urlsplit(token)
        except ValueError:
            continue
        if parsed.scheme.lower() in ("http", "https") and parsed.hostname:
            urls.append(token)
    return list(dict.fromkeys(urls))


def is_playlist_url(url: str) -> bool:
    """
    Checks if a URL points to an actual created playlist.
    Specifically excludes auto-generated YouTube Mixes (list=RD...).
    Returns True for:
    - Spotify playlists and albums
    - Direct playlist pages: youtube.com/playlist?list=...
    - User/Channel created playlists: list=PL..., list=OLAK..., list=UU..., list=FL..., list=LL...
    """
    if not url:
        return False

    # Check for Spotify playlist or album
    if is_spotify_playlist_or_album(url):
        return True

    host = (urllib.parse.urlsplit(url).hostname or "").lower()
    if host not in ("youtube.com", "www.youtube.com", "music.youtube.com", "m.youtube.com", "youtu.be"):
        return False

    # Check for direct /playlist?list= page
    if "/playlist" in url and "list=" in url:
        # Check if it's an auto-generated mix (RD)
        match = YT_PLAYLIST_PARAM_REGEX.search(url)
        if match and match.group(1).upper().startswith("RD"):
            return False
        return True

    # Check for video link with a playlist attached
    match = YT_PLAYLIST_PARAM_REGEX.search(url)
    if match:
        playlist_id = match.group(1)
        # Exclude auto-generated YouTube default mixes (starts with RD)
        if playlist_id.upper().startswith("RD"):
            return False
        # Only treat standard user playlists or albums as playlists
        return True

    return False

def get_playlist_id(url: str) -> str:
    """Extracts playlist ID from a URL."""
    match = YT_PLAYLIST_PARAM_REGEX.search(url)
    if match:
        return match.group(1)
    return ""

def extract_video_id(url: str) -> Optional[str]:
    """Extracts the 11-character YouTube video ID from any video URL."""
    if not url:
        return None
    match = YT_VIDEO_REGEX.search(url)
    if match:
        return match.group(5)
    return None

def clean_video_url(url: str) -> str:
    """
    Extracts clean single track/video URL.
    For YouTube: extracts https://www.youtube.com/watch?v=VIDEO_ID (stripping &list=RD...).
    For Spotify: keeps clean track URL (stripping tracking query params like ?si=...).
    """
    if not url:
        return url
    if is_spotify_url(url):
        return url.split("?")[0]
    match = YT_VIDEO_REGEX.search(url)
    if match:
        video_id = match.group(5)
        return f"https://www.youtube.com/watch?v={video_id}"
    return url

def fetch_playlist_entries(
    playlist_url: str,
    ffmpeg_path: str = None
) -> Tuple[str, List[Dict[str, Any]]]:
    """
    Fetches the entries of a created playlist (YouTube or Spotify) without downloading audio.
    Returns (playlist_title, list_of_entry_dicts).
    """
    if is_spotify_url(playlist_url):
        title, tracks = fetch_spotify_collection(playlist_url)
        entries = []
        for t in tracks:
            entries.append({
                'id': t['id'],
                'url': t['spotify_url'],
                'title': t['title'],
                'duration': t['duration'],
                'uploader': t['artist'],
                'thumbnail_url': t.get('cover_url', ''),
                'search_query': t.get('search_query', '')
            })
        return title, entries

    ydl_opts = {
        'extract_flat': 'in_playlist',
        'skip_download': True,
        'quiet': True,
        'no_warnings': True,
        'ignoreerrors': False,
        'socket_timeout': 20,
        'retries': 2,
    }
    if ffmpeg_path:
        ydl_opts['ffmpeg_location'] = ffmpeg_path

    entries = []
    playlist_title = "YouTube Playlist"

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        try:
            info = ydl.extract_info(playlist_url, download=False)
            if not info:
                return playlist_title, []

            if 'title' in info and info['title']:
                playlist_title = info['title']

            raw_entries = info.get('entries', [])
            for item in raw_entries:
                if not item:
                    continue
                vid_id = item.get('id')
                vid_url = item.get('webpage_url') or item.get('url')
                if not vid_url or not vid_url.startswith(('http://', 'https://')):
                    vid_url = f'https://www.youtube.com/watch?v={vid_id}' if vid_id and 'youtube' in str(item.get('ie_key', info.get('extractor', ''))).lower() else None
                if not vid_url:
                    continue

                title = item.get('title') or f"Video {vid_id}"
                duration = item.get('duration') or 0
                uploader = item.get('uploader') or item.get('channel') or "YouTube"

                entries.append({
                    'id': vid_id,
                    'url': vid_url,
                    'title': title,
                    'duration': duration,
                    'uploader': uploader
                })
        except Exception as e:
            print(f"[URL Parser] Error extracting playlist: {e}")
            raise e

    return playlist_title, entries
