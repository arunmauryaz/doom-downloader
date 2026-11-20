"""
Universal Media Scraper for Doom Downloader Engine.
Detects, extracts, and resolves media from any URL:
  - Spotify tracks, albums, and playlists
  - YouTube videos, shorts, and playlists
  - Social & video platforms (Bilibili, Twitter/X, Instagram, TikTok, Reddit, Vimeo, Twitch, Facebook)
  - Obfuscated JavaScript players (Dean Edwards P.A.C.K.E.R., packed/eval js)
  - Single-Page Applications (SPA / Next.js __NEXT_DATA__, Nuxt.js)
  - Schema.org JSON-LD VideoObject metadata
  - HTML5 video tags, OpenGraph video, and embedded iframe players
  - HLS (.m3u8) and DASH (.mpd) streaming manifests with anti-hotlinking headers
  - Direct downloadable files (PDF, ZIP, ISO, EXE, media files, etc.)
  - TLS impersonation via curl_cffi to bypass Cloudflare / Akamai anti-bot fingerprinting
"""

import os
import re
import json
import urllib.parse
from typing import Dict, Any, List, Optional, Tuple
import requests
from bs4 import BeautifulSoup

from .spotify import (
    is_spotify_url, is_spotify_playlist_or_album,
    fetch_spotify_track, fetch_spotify_collection
)
from .url_parser import is_playlist_url, fetch_playlist_entries
from .formats import (
    FORMAT_NAMES, VIDEO_FORMAT_NAMES, DEFAULT_FORMAT, FILE_FORMAT
)

# Realistic browser headers matching a modern Windows 11 Chrome client
BROWSER_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,video/*,image/avif,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Sec-Ch-Ua": '"Chromium";v="124", "Google Chrome";v="124", "Not-A.Brand";v="99"',
    "Sec-Ch-Ua-Mobile": "?0",
    "Sec-Ch-Ua-Platform": '"Windows"',
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "none",
    "Sec-Fetch-User": "?1",
    "Upgrade-Insecure-Requests": "1",
}

DIRECT_FILE_EXTENSIONS = (
    ".pdf", ".zip", ".tar", ".gz", ".7z", ".rar", ".iso", ".exe", ".msi",
    ".docx", ".xlsx", ".pptx", ".txt", ".csv", ".json", ".xml", ".bin",
    ".apk", ".dmg", ".pkg", ".deb", ".rpm"
)

DIRECT_AUDIO_EXTENSIONS = (".mp3", ".wav", ".flac", ".m4a", ".aac", ".ogg", ".opus")
DIRECT_VIDEO_EXTENSIONS = (".mp4", ".webm", ".mkv", ".m4v", ".mov", ".avi", ".ts", ".m3u8", ".mpd")


# =========================================================================
# 1. Dean Edwards P.A.C.K.E.R. JavaScript Unpacker
# =========================================================================

def unpack_dean_edwards_packer(payload: str) -> str:
    """
    Unpacks Dean Edwards P.A.C.K.E.R. obfuscated JavaScript.
    Commonly used on video streaming / hosting platforms (e.g. Streamtape, Mixdrop, Dood, etc.)
    to hide .m3u8, .mpd, or direct .mp4 streaming links.
    """
    pattern = re.compile(
        r'''eval\s*\(\s*function\s*\(\s*p\s*,\s*a\s*,\s*c\s*,\s*k\s*,\s*e\s*,\s*[dr]\s*\)[\s\S]+?\}\s*\(\s*(['"][\s\S]+?['"])\s*,\s*(\d+)\s*,\s*(\d+)\s*,\s*(['"][\s\S]+?['"])\.split\(\s*['"]\|['"]\s*\)(?:[^\)]*)\)\s*\)''',
        re.DOTALL
    )

    chars = '0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ'

    def base_n(num: int, b: int) -> str:
        if num == 0:
            return chars[0]
        digits = []
        while num > 0:
            digits.append(chars[num % b])
            num //= b
        return ''.join(reversed(digits))

    def replacer(match):
        try:
            p, a, c, k = match.groups()
            a = int(a)
            c = int(c)
            p_str = p[1:-1]
            try:
                p_str = p_str.encode('utf-8').decode('unicode-escape')
            except Exception:
                pass
            words = k[1:-1].split('|')

            lookup = {}
            for i in range(c):
                key = base_n(i, a)
                val = words[i] if i < len(words) and words[i] else key
                lookup[key] = val

            def word_replace(w_match):
                word = w_match.group(0)
                return lookup.get(word, word)

            unpacked = re.sub(r'\b[0-9a-zA-Z]+\b', word_replace, p_str)
            return unpacked
        except Exception:
            return match.group(0)

    return pattern.sub(replacer, payload)


# =========================================================================
# 2. Modern HTTP Fetcher with TLS Impersonation (Bypasses Cloudflare / Akamai)
# =========================================================================

def fetch_page_content(
    url: str,
    headers: Optional[Dict[str, str]] = None,
    timeout: int = 12
) -> Tuple[int, str, Dict[str, str]]:
    """
    Fetches web content using curl_cffi with Chrome 124 TLS impersonation.
    Bypasses Cloudflare JA3/JA4 TLS fingerprint filtering.
    Falls back gracefully to requests.Session if curl_cffi encounters an error.
    Returns (status_code, text, response_headers).
    """
    req_headers = BROWSER_HEADERS.copy()
    if headers:
        req_headers.update(headers)

    # Attempt 1: curl_cffi Chrome impersonation
    try:
        import curl_cffi.requests
        session = curl_cffi.requests.Session(impersonate="chrome124")
        resp = session.get(url, headers=req_headers, timeout=timeout)
        return resp.status_code, resp.text, dict(resp.headers)
    except Exception:
        pass

    # Attempt 2: Standard requests fallback
    try:
        session = requests.Session()
        resp = session.get(url, headers=req_headers, timeout=timeout)
        return resp.status_code, resp.text, dict(resp.headers)
    except Exception as e:
        return 0, "", {}


# =========================================================================
# 3. Twitter / X Direct Video Fallback (via Syndication / vxtwitter)
# =========================================================================

def fetch_twitter_video_fallback(url: str, timeout: int = 10) -> Optional[Dict[str, Any]]:
    """
    Extracts direct video stream from Twitter/X tweets using vxtwitter syndication API.
    Bypasses Twitter login walls, rate-limits, and guest-token errors.
    """
    match = re.search(r'(?:twitter\.com|x\.com)/([^/]+)/status/(\d+)', url)
    if not match:
        return None
    username, status_id = match.groups()
    api_url = f"https://api.vxtwitter.com/{username}/status/{status_id}"

    try:
        status_code, body, _ = fetch_page_content(api_url, timeout=timeout)
        if status_code == 200 and body:
            data = json.loads(body)
            media_urls = data.get("mediaURLs", [])
            video_url = data.get("video_url")
            if not video_url and media_urls:
                for m in media_urls:
                    if m.endswith((".mp4", ".m3u8")):
                        video_url = m
                        break

            if video_url:
                title = data.get("text", "Twitter Video")
                # Truncate title to first line or 80 chars
                first_line = title.split("\n")[0].strip()
                if len(first_line) > 80:
                    first_line = first_line[:77] + "..."
                return {
                    "platform": "Twitter / X",
                    "media_type": "video",
                    "title": f"{data.get('user_name', username)}: {first_line}",
                    "artist": data.get("user_name", username),
                    "thumbnail_url": data.get("media_thumb_url", "") or (media_urls[0] if media_urls else ""),
                    "stream_url": video_url,
                    "http_headers": {
                        "Referer": "https://x.com/",
                        "User-Agent": BROWSER_HEADERS["User-Agent"]
                    }
                }
    except Exception:
        pass
    return None


# =========================================================================
# 4. Universal Media Scraper and Resolver
# =========================================================================

def detect_and_resolve_media(
    url: str,
    ffmpeg_dir: Optional[str] = None,
    expand_collections: bool = False,
    timeout: int = 12
) -> Dict[str, Any]:
    """
    Intelligently inspects any link, detects what type of media it contains,
    extracts metadata/thumbnails, and provides context-adaptive format options.
    """
    clean_url = url.strip()
    from .bilibili import is_bilibili_url, clean_bilibili_url
    if is_bilibili_url(clean_url):
        clean_url = clean_bilibili_url(clean_url)

    parsed = urllib.parse.urlparse(clean_url)
    path_lower = parsed.path.lower()

    result: Dict[str, Any] = {
        "url": clean_url,
        "media_type": "unknown",       # "spotify_audio", "video", "audio", "direct_file", "collection"
        "platform": "Web",             # "Spotify", "YouTube", "Web Video", "Direct File"
        "title": "Unknown Media",
        "artist": "",
        "duration": 0,
        "thumbnail_url": "",
        "stream_url": None,
        "http_headers": {},
        "is_collection": False,
        "entries": [],
        "available_formats": [],
        "default_format": DEFAULT_FORMAT,
    }

    # ---------------- 1. Spotify ----------------
    if is_spotify_url(clean_url):
        result["platform"] = "Spotify"
        result["media_type"] = "spotify_audio"
        result["available_formats"] = list(FORMAT_NAMES)
        result["default_format"] = DEFAULT_FORMAT

        if is_spotify_playlist_or_album(clean_url):
            result["is_collection"] = True
            result["media_type"] = "collection"
            if expand_collections:
                title, tracks = fetch_spotify_collection(clean_url)
                result["title"] = title
                result["entries"] = tracks
            else:
                title, _ = fetch_spotify_collection(clean_url)
                result["title"] = title
        else:
            track = fetch_spotify_track(clean_url)
            if track:
                result["title"] = track.get("title", "Spotify Track")
                result["artist"] = track.get("artist", "")
                result["duration"] = track.get("duration", 0)
                result["thumbnail_url"] = track.get("cover_url", "")
        return result

    # ---------------- 2. Created Playlists / Collections ----------------
    if is_playlist_url(clean_url):
        result["platform"] = "YouTube" if ("youtube.com" in clean_url or "youtu.be" in clean_url) else "Web"
        result["is_collection"] = True
        result["media_type"] = "collection"
        result["available_formats"] = list(VIDEO_FORMAT_NAMES) + [f"[Audio] {f}" for f in FORMAT_NAMES]
        result["default_format"] = "MP4 · Best available"

        if expand_collections:
            try:
                title, entries = fetch_playlist_entries(clean_url, ffmpeg_dir)
                result["title"] = title
                result["entries"] = entries
            except Exception as e:
                result["error"] = str(e)
        return result

    # ---------------- 3. Direct File / Document Links ----------------
    if path_lower.endswith(DIRECT_FILE_EXTENSIONS):
        filename = os.path.basename(parsed.path) or "downloaded_file"
        result["platform"] = "Direct File"
        result["media_type"] = "direct_file"
        result["title"] = urllib.parse.unquote(filename)
        result["available_formats"] = [FILE_FORMAT]
        result["default_format"] = FILE_FORMAT
        return result

    # ---------------- 4. Direct Audio or Video File Streams ----------------
    if path_lower.endswith(DIRECT_AUDIO_EXTENSIONS):
        filename = os.path.basename(parsed.path) or "audio_file"
        result["platform"] = "Direct Audio"
        result["media_type"] = "audio"
        result["title"] = urllib.parse.unquote(filename)
        result["available_formats"] = [FILE_FORMAT] + list(FORMAT_NAMES)
        result["default_format"] = FILE_FORMAT
        return result

    if path_lower.endswith(DIRECT_VIDEO_EXTENSIONS):
        filename = os.path.basename(parsed.path) or "video_file"
        result["platform"] = "Direct Video"
        result["media_type"] = "video"
        result["title"] = urllib.parse.unquote(filename)
        result["stream_url"] = clean_url
        result["available_formats"] = list(VIDEO_FORMAT_NAMES) + [f"[Audio] {f}" for f in FORMAT_NAMES]
        result["default_format"] = "MP4 · Best available"
        return result

    # ---------------- 4.5 Steam Game Store Trailers ----------------
    if "store.steampowered.com/app/" in clean_url:
        steam_match = re.search(r"store\.steampowered\.com/app/(\d+)", clean_url)
        if steam_match:
            app_id = steam_match.group(1)
            try:
                api_url = f"https://store.steampowered.com/api/appdetails?appids={app_id}&cc=us&l=en"
                status_code, body, _ = fetch_page_content(api_url, timeout=timeout)
                if status_code == 200 and body:
                    steam_data = json.loads(body).get(app_id, {})
                    if steam_data.get("success"):
                        app_info = steam_data.get("data", {})
                        game_name = app_info.get("name", "Steam Game")
                        movies = app_info.get("movies", [])
                        header_img = app_info.get("header_image", "")
                        if movies:
                            entries = []
                            for idx, mov in enumerate(movies):
                                mov_name = mov.get("name") or f"Trailer {idx + 1}"
                                stream = (
                                    mov.get("hls_h264")
                                    or mov.get("dash_h264")
                                    or (mov.get("mp4") or {}).get("max")
                                    or (mov.get("webm") or {}).get("max")
                                )
                                thumb = mov.get("thumbnail") or header_img
                                if stream:
                                    entries.append({
                                        "id": str(mov.get("id", idx)),
                                        "title": f"{game_name} - {mov_name}",
                                        "artist": "Valve / Steam",
                                        "url": stream,
                                        "stream_url": stream,
                                        "thumbnail_url": thumb,
                                        "duration": 0
                                    })

                            if len(entries) > 1:
                                result["platform"] = "Steam"
                                result["media_type"] = "collection"
                                result["is_collection"] = True
                                result["title"] = f"{game_name} ({len(entries)} Trailers)"
                                result["artist"] = "Valve / Steam"
                                result["thumbnail_url"] = entries[0]["thumbnail_url"]
                                result["entries"] = entries
                                result["collection_count"] = len(entries)
                                result["available_formats"] = list(VIDEO_FORMAT_NAMES) + [f"[Audio] {f}" for f in FORMAT_NAMES]
                                result["default_format"] = "MP4 · Best available"
                                return result
                            elif len(entries) == 1:
                                result["platform"] = "Steam"
                                result["media_type"] = "video"
                                result["is_collection"] = False
                                result["title"] = entries[0]["title"]
                                result["artist"] = "Valve / Steam"
                                result["thumbnail_url"] = entries[0]["thumbnail_url"]
                                result["stream_url"] = entries[0]["stream_url"]
                                result["entries"] = entries
                                result["available_formats"] = list(VIDEO_FORMAT_NAMES) + [f"[Audio] {f}" for f in FORMAT_NAMES]
                                result["default_format"] = "MP4 · Best available"
                                return result
            except Exception:
                pass

    # ---------------- 5. Platform Extractors via yt-dlp ----------------
    # Supports YouTube, Vimeo, Twitter/X, Instagram, Reddit, TikTok, Facebook, Bilibili, etc.
    import yt_dlp
    from .config import config
    browser_cookies = config.get("browser_cookies", "none")

    ydl_opts = {
        "skip_download": True,
        "quiet": True,
        "no_warnings": True,
        "ignoreerrors": False,
        "socket_timeout": timeout,
        "retries": 1,
        "noplaylist": not expand_collections,
    }
    if ffmpeg_dir:
        ydl_opts["ffmpeg_location"] = ffmpeg_dir
    if is_bilibili_url(clean_url):
        from .bilibili import BILIBILI_HEADERS
        ydl_opts["http_headers"] = BILIBILI_HEADERS

    if browser_cookies and browser_cookies.lower() != "none":
        ydl_opts["cookiesfrombrowser"] = (browser_cookies.lower(),)

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(clean_url, download=False)
            if info:
                raw_entries = info.get("entries")
                if raw_entries and (info.get("_type") == "playlist" or len(raw_entries) > 1):
                    parsed_entries = []
                    for idx, e in enumerate(raw_entries):
                        if not e:
                            continue
                        e_thumb = ""
                        if e.get("thumbnails"):
                            e_thumb = e["thumbnails"][-1].get("url", "")
                        else:
                            e_thumb = e.get("thumbnail", "")
                        parsed_entries.append({
                            "id": str(e.get("id", idx)),
                            "title": e.get("title", f"Video {idx + 1}"),
                            "artist": e.get("uploader") or e.get("channel", ""),
                            "url": e.get("webpage_url") or e.get("url", clean_url),
                            "stream_url": e.get("url") if (e.get("url") and e.get("url").startswith("http")) else None,
                            "thumbnail_url": e_thumb,
                            "duration": e.get("duration", 0)
                        })
                    if parsed_entries:
                        result["platform"] = (info.get("extractor_key") or "Collection").replace("Generic", "Collection").capitalize()
                        result["media_type"] = "collection"
                        result["is_collection"] = True
                        result["title"] = info.get("title") or f"Collection ({len(parsed_entries)} videos)"
                        result["artist"] = info.get("uploader") or info.get("channel") or ""
                        result["thumbnail_url"] = parsed_entries[0]["thumbnail_url"] if parsed_entries else ""
                        result["entries"] = parsed_entries
                        result["collection_count"] = len(parsed_entries)
                        result["available_formats"] = list(VIDEO_FORMAT_NAMES) + [f"[Audio] {f}" for f in FORMAT_NAMES]
                        result["default_format"] = "MP4 · Best available"
                        return result
                ext_raw = (info.get("extractor_key") or info.get("extractor") or "").lower()
                host_lower = parsed.netloc.lower()
                if "twitter" in ext_raw or ext_raw == "x" or "twitter.com" in host_lower or "x.com" in host_lower:
                    platform_name = "Twitter / X"
                elif "instagram" in ext_raw or "instagram.com" in host_lower:
                    platform_name = "Instagram"
                elif "facebook" in ext_raw or "facebook.com" in host_lower or "fb.watch" in host_lower:
                    platform_name = "Facebook"
                elif "tiktok" in ext_raw or "tiktok.com" in host_lower:
                    platform_name = "TikTok"
                elif "reddit" in ext_raw or "reddit.com" in host_lower:
                    platform_name = "Reddit"
                elif "twitch" in ext_raw or "twitch.tv" in host_lower:
                    platform_name = "Twitch"
                elif "youtube" in ext_raw or "youtube.com" in host_lower or "youtu.be" in host_lower:
                    platform_name = "YouTube"
                elif "steam" in ext_raw or "steampowered.com" in host_lower:
                    platform_name = "Steam"
                elif "bilibili" in ext_raw or "bilibili.com" in host_lower or "b23.tv" in host_lower:
                    platform_name = "Bilibili"
                elif "vimeo" in ext_raw:
                    platform_name = "Vimeo"
                elif "soundcloud" in ext_raw:
                    platform_name = "SoundCloud"
                    result["media_type"] = "audio"
                else:
                    platform_name = info.get("extractor_key") or "Web Video"
                    platform_name = platform_name.replace("Generic", "Web Video").capitalize()

                result["platform"] = platform_name
                result["media_type"] = "video"
                result["title"] = info.get("title") or "Web Video"
                result["artist"] = info.get("uploader") or info.get("channel") or ""
                result["duration"] = info.get("duration") or 0
                thumbnails = info.get("thumbnails", [])
                if thumbnails:
                    result["thumbnail_url"] = thumbnails[-1].get("url", "")
                else:
                    result["thumbnail_url"] = info.get("thumbnail", "")

                result["available_formats"] = list(VIDEO_FORMAT_NAMES) + [f"[Audio] {f}" for f in FORMAT_NAMES]
                result["default_format"] = "MP4 · Best available"
                return result

    except Exception:
        # Check platform-specific syndication fallback (e.g. Twitter / X)
        if "twitter.com" in parsed.netloc.lower() or "x.com" in parsed.netloc.lower():
            fb = fetch_twitter_video_fallback(clean_url, timeout=timeout)
            if fb:
                fb["available_formats"] = list(VIDEO_FORMAT_NAMES) + [f"[Audio] {f}" for f in FORMAT_NAMES]
                fb["default_format"] = "MP4 · Best available"
                return fb

    # ---------------- 6. Universal HTML Page Video Scraper ----------------
    # Scrapes HTML, un-obfuscates packed JS, inspects JSON-LD Schema, Next.js hydration,
    # HTML5 video tags, OpenGraph video, and embedded streaming manifests (.m3u8 / .mpd).
    try:
        status_code, body, resp_headers = fetch_page_content(clean_url, timeout=timeout)
        if status_code == 200 and body:
            content_type = resp_headers.get("content-type", "").lower()

            # Non-HTML file stream
            if "application/" in content_type or "image/" in content_type:
                result["platform"] = "Direct File"
                result["media_type"] = "direct_file"
                name = os.path.basename(parsed.path) or "download"
                result["title"] = urllib.parse.unquote(name)
                result["available_formats"] = [FILE_FORMAT]
                result["default_format"] = FILE_FORMAT
                return result

            # Parse HTML
            soup = BeautifulSoup(body, "html.parser")

            # Extract Title
            title = ""
            og_title = soup.find("meta", property="og:title")
            if og_title and og_title.get("content"):
                title = og_title["content"].strip()
            elif soup.title and soup.title.string:
                title = soup.title.string.strip()

            # Extract Thumbnail
            thumb = ""
            og_img = soup.find("meta", property="og:image") or soup.find("meta", attrs={"name": "twitter:image"})
            if og_img and og_img.get("content"):
                thumb = urllib.parse.urljoin(clean_url, og_img["content"].strip())

            video_url = None

            # 6A. Schema.org JSON-LD VideoObject Check
            for script_ld in soup.find_all("script", type="application/ld+json"):
                try:
                    ld_content = json.loads(script_ld.string or "")
                    items = ld_content if isinstance(ld_content, list) else ld_content.get("@graph", [ld_content])
                    for item in items:
                        if isinstance(item, dict) and item.get("@type") == "VideoObject":
                            cand_url = item.get("contentUrl") or item.get("embedUrl")
                            if cand_url:
                                video_url = cand_url
                                if item.get("name"):
                                    title = item["name"]
                                if item.get("thumbnailUrl") and not thumb:
                                    t = item["thumbnailUrl"]
                                    thumb = t[0] if isinstance(t, list) else t
                                break
                    if video_url:
                        break
                except Exception:
                    pass

            # 6B. Check Next.js Hydration State (__NEXT_DATA__)
            if not video_url:
                next_data_script = soup.find("script", id="__NEXT_DATA__")
                if next_data_script and next_data_script.string:
                    try:
                        next_json = json.loads(next_data_script.string)
                        raw_json_str = json.dumps(next_json)
                        m3u8_m = re.findall(r'(https?:\\?/\\?/[^\s"\'<>]+\.m3u8[^\s"\'<>]*)', raw_json_str)
                        if m3u8_m:
                            video_url = m3u8_m[0].replace(r"\/", "/")
                        else:
                            mp4_m = re.findall(r'(https?:\\?/\\?/[^\s"\'<>]+\.mp4[^\s"\'<>]*)', raw_json_str)
                            if mp4_m:
                                video_url = mp4_m[0].replace(r"\/", "/")
                    except Exception:
                        pass

            # 6C. Check <video src="..."> and <source src="...">
            if not video_url:
                video_tag = soup.find("video")
                if video_tag:
                    if video_tag.get("src"):
                        video_url = urllib.parse.urljoin(clean_url, video_tag["src"])
                    elif video_tag.get("poster") and not thumb:
                        thumb = urllib.parse.urljoin(clean_url, video_tag["poster"])

                    if not video_url:
                        source_tag = video_tag.find("source")
                        if source_tag and source_tag.get("src"):
                            video_url = urllib.parse.urljoin(clean_url, source_tag["src"])

            # 6D. Check OpenGraph video: <meta property="og:video" content="...">
            if not video_url:
                for prop in ("og:video", "og:video:url", "og:video:secure_url", "twitter:player:stream"):
                    meta_v = soup.find("meta", property=prop) or soup.find("meta", attrs={"name": prop})
                    if meta_v and meta_v.get("content"):
                        cand = meta_v["content"].strip()
                        if cand.startswith("http"):
                            if is_bilibili_url(cand):
                                cand = clean_bilibili_url(cand)
                            cand_path = urllib.parse.urlsplit(cand).path.lower()
                            if not cand_path.endswith((".html", ".htm", ".php", ".aspx", ".jsp")):
                                video_url = cand
                                break

            # 6E. Check for embedded iframe player (YouTube, Vimeo, Dailymotion, etc.)
            if not video_url:
                for iframe in soup.find_all("iframe"):
                    src = iframe.get("src", "")
                    if "youtube.com/embed" in src or "player.vimeo.com" in src or "dailymotion.com/embed" in src:
                        if src.startswith("//"):
                            src = "https:" + src
                        video_url = src
                        break

            # 6F. Dean Edwards P.A.C.K.E.R. Unpacking & Script Scanning
            if not video_url:
                all_script_text = "\n".join(s.string or "" for s in soup.find_all("script") if s.string)
                # Unpack any obfuscated packed JS
                unpacked_text = unpack_dean_edwards_packer(all_script_text)
                combined_scripts = all_script_text + "\n" + unpacked_text

                # Search for player configs (jwplayer, videojs, sources)
                player_match = re.search(r'''(?:file|source|src)\s*:\s*["'](https?:\\?/\\?/[^"']+\.(?:m3u8|mp4|mpd)[^"']*)["']''', combined_scripts, re.I)
                if player_match:
                    video_url = player_match.group(1).replace(r"\/", "/")

                # Search for direct .m3u8 HLS manifests
                if not video_url:
                    m3u8_matches = re.findall(r'(https?:\\?/\\?/[^\s"\'<>]+\.m3u8[^\s"\'<>]*)', combined_scripts)
                    if m3u8_matches:
                        video_url = m3u8_matches[0].replace(r"\/", "/")

                # Search for direct .mpd DASH manifests
                if not video_url:
                    mpd_matches = re.findall(r'(https?:\\?/\\?/[^\s"\'<>]+\.mpd[^\s"\'<>]*)', combined_scripts)
                    if mpd_matches:
                        video_url = mpd_matches[0].replace(r"\/", "/")

                # Search for direct .mp4 streaming files
                if not video_url:
                    mp4_matches = re.findall(r'(https?:\\?/\\?/[^\s"\'<>]+\.mp4[^\s"\'<>]*)', combined_scripts)
                    if mp4_matches:
                        video_url = mp4_matches[0].replace(r"\/", "/")

            if video_url:
                domain = parsed.netloc.replace("www.", "")
                result["platform"] = f"Web Video ({domain})"
                result["media_type"] = "video"
                result["title"] = title or f"Video from {domain}"
                result["thumbnail_url"] = thumb
                result["stream_url"] = video_url
                # Preserve Origin and Referer so streaming chunks and anti-hotlinking CDNs succeed
                result["http_headers"] = {
                    "Referer": clean_url,
                    "Origin": f"{parsed.scheme}://{parsed.netloc}",
                    "User-Agent": BROWSER_HEADERS["User-Agent"]
                }
                result["available_formats"] = list(VIDEO_FORMAT_NAMES) + [f"[Audio] {f}" for f in FORMAT_NAMES]
                result["default_format"] = "MP4 · Best available"
                return result

    except Exception as e:
        result["error"] = str(e)

    # Fallback default
    result["title"] = clean_url
    result["available_formats"] = list(VIDEO_FORMAT_NAMES) + list(FORMAT_NAMES) + [FILE_FORMAT]
    result["default_format"] = DEFAULT_FORMAT
    return result
