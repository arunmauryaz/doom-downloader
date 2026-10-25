"""
Spotify URL detection and metadata extraction module.
Resolves Spotify tracks, albums, and playlists into structured metadata
without requiring Spotify API credentials or tokens.
"""

import re
import json
import requests
from typing import List, Dict, Any, Tuple, Optional

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}

def is_spotify_url(url: str) -> bool:
    """Checks if a URL belongs to Spotify."""
    if not url:
        return False
    return "open.spotify.com" in url or "spotify.link" in url or url.startswith("spotify:")

def is_spotify_playlist_or_album(url: str) -> bool:
    """Checks if the URL is a Spotify playlist or album."""
    if not is_spotify_url(url):
        return False
    return "/playlist/" in url or "/album/" in url or ":playlist:" in url or ":album:" in url

def is_spotify_track(url: str) -> bool:
    """Checks if the URL is a single Spotify track."""
    if not is_spotify_url(url):
        return False
    return "/track/" in url or ":track:" in url

def resolve_spotify_url(url: str) -> str:
    """Expands shortened spotify.link or converts URI to open.spotify.com URL."""
    if "spotify.link" in url:
        try:
            r = requests.head(url, headers=HEADERS, allow_redirects=True, timeout=8)
            return r.url
        except Exception:
            pass
    if url.startswith("spotify:"):
        parts = url.split(":")
        if len(parts) >= 3:
            return f"https://open.spotify.com/{parts[1]}/{parts[2]}"
    return url

def fetch_spotify_track(url: str) -> Optional[Dict[str, Any]]:
    """
    Fetches title, artist, duration, and high-resolution cover art for a Spotify track.
    Returns metadata dictionary or None if fetch fails.
    """
    clean_url = resolve_spotify_url(url)
    match = re.search(r'open\.spotify\.com/track/([a-zA-Z0-9]+)', clean_url)
    if not match:
        return None
    track_id = match.group(1)
    embed_url = f"https://open.spotify.com/embed/track/{track_id}"
    try:
        r = requests.get(embed_url, headers=HEADERS, timeout=10)
        if r.status_code != 200:
            return None
        m = re.search(r'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>', r.text)
        if m:
            data = json.loads(m.group(1))
            entity = data.get('props', {}).get('pageProps', {}).get('state', {}).get('data', {}).get('entity', {})
            title = entity.get('name', 'Unknown Track')
            artists_list = entity.get('artists', [])
            artist = ", ".join([a.get('name') for a in artists_list if a.get('name')]) or "Unknown Artist"
            duration = int(entity.get('duration', 0) / 1000)
            images = entity.get('visualIdentity', {}).get('image', [])
            cover_url = ""
            if images:
                images_sorted = sorted(images, key=lambda x: x.get('maxHeight') or 0, reverse=True)
                cover_url = images_sorted[0].get('url', '')

            return {
                "id": track_id,
                "title": title,
                "artist": artist,
                "duration": duration,
                "cover_url": cover_url,
                "spotify_url": f"https://open.spotify.com/track/{track_id}",
                "search_query": f"{artist} - {title} audio"
            }
    except Exception as e:
        print(f"[Spotify] Error fetching track info: {e}")
    return None

def fetch_spotify_collection(url: str) -> Tuple[str, List[Dict[str, Any]]]:
    """
    Fetches title and all tracks from a Spotify playlist or album.
    Returns (collection_title, list_of_track_dicts).
    """
    clean_url = resolve_spotify_url(url)
    is_playlist = "/playlist/" in clean_url
    collection_type = "playlist" if is_playlist else "album"
    match = re.search(r'open\.spotify\.com/(playlist|album)/([a-zA-Z0-9]+)', clean_url)
    if not match:
        return "Spotify Collection", []

    item_id = match.group(2)
    embed_url = f"https://open.spotify.com/embed/{collection_type}/{item_id}"
    try:
        r = requests.get(embed_url, headers=HEADERS, timeout=12)
        if r.status_code != 200:
            return "Spotify Collection", []
        m = re.search(r'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>', r.text)
        if m:
            data = json.loads(m.group(1))
            entity = data.get('props', {}).get('pageProps', {}).get('state', {}).get('data', {}).get('entity', {})
            collection_name = entity.get('name', f"Spotify {collection_type.capitalize()}")
            images = entity.get('visualIdentity', {}).get('image', [])
            default_cover = ""
            if images:
                images_sorted = sorted(images, key=lambda x: x.get('maxHeight') or 0, reverse=True)
                default_cover = images_sorted[0].get('url', '')

            track_list = entity.get('trackList', [])
            entries = []
            for t in track_list:
                t_title = t.get('title', 'Unknown Title')
                t_artist = t.get('subtitle', 'Unknown Artist')
                t_duration = int(t.get('duration', 0) / 1000)
                t_uri = t.get('uri', '')
                t_id = t_uri.split(":")[-1] if t_uri else ""
                t_url = f"https://open.spotify.com/track/{t_id}" if t_id else ""
                entries.append({
                    "id": t_id,
                    "title": t_title,
                    "artist": t_artist,
                    "duration": t_duration,
                    "cover_url": default_cover,
                    "spotify_url": t_url,
                    "search_query": f"{t_artist} - {t_title} audio"
                })
            return collection_name, entries
    except Exception as e:
        print(f"[Spotify] Error fetching collection info: {e}")
    return "Spotify Collection", []

def resolve_spotify_to_youtube(artist: str, title: str, ffmpeg_path: Optional[str] = None) -> Optional[str]:
    """
    Searches YouTube Music/YouTube for the optimal audio track matching the Spotify song.
    Returns the YouTube webpage URL.
    """
    import yt_dlp
    query = f"ytsearch1:{artist} - {title} audio"
    opts = {
        'quiet': True,
        'no_warnings': True,
        'extract_flat': True,
        'skip_download': True
    }
    if ffmpeg_path:
        opts['ffmpeg_location'] = ffmpeg_path

    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            r = ydl.extract_info(query, download=False)
            if r and 'entries' in r and len(r['entries']) > 0:
                e = r['entries'][0]
                eid = e.get('id')
                return e.get('url') or (f"https://www.youtube.com/watch?v={eid}" if eid else None)
    except Exception as e:
        print(f"[Spotify] Error resolving YouTube audio: {e}")
    return None
