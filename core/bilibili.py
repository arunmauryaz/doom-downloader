"""
Bilibili extractor and URL resolver for Doom Downloader.
Handles standard video URLs (BV/av), shortlinks (b23.tv), Bangumi anime, embedded player URLs, and multi-part videos.
Ensures proper HTTP Referer and User-Agent headers to prevent 403 Forbidden and CDN blocking.
"""

import re
import urllib.parse
from typing import Optional, Dict, Any
import requests

BILIBILI_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Referer": "https://www.bilibili.com/",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9,zh-CN;q=0.8,zh;q=0.7",
}

BVID_REGEX = re.compile(r'\b(BV[a-zA-Z0-9]{10})\b', re.IGNORECASE)
AVID_REGEX = re.compile(r'(?:\bav|aid=)(\d+)\b', re.IGNORECASE)

BILIBILI_SHORT_REGEX = re.compile(
    r'https?://(?:b23\.tv|bili2233\.cn)/([a-zA-Z0-9]+)',
    re.IGNORECASE
)

BILIBILI_BANGUMI_REGEX = re.compile(
    r'https?://(?:www\.)?bilibili\.com/bangumi/play/(ep\d+|ss\d+)',
    re.IGNORECASE
)


def is_bilibili_url(url: str) -> bool:
    """Checks whether the given URL is a Bilibili video, bangumi, shortlink, or audio."""
    if not url:
        return False
    low = url.lower()
    return (
        "bilibili.com" in low or
        "b23.tv" in low or
        "bili2233.cn" in low or
        "bilibili.tv" in low or
        "biliintl.com" in low or
        bool(BVID_REGEX.search(url))
    )


def resolve_bilibili_shortlink(url: str, timeout: int = 5) -> str:
    """
    Expands b23.tv or bili2233.cn shortlinks by following HTTP 302 redirects
    to the canonical Bilibili URL.
    """
    if "b23.tv" not in url.lower() and "bili2233.cn" not in url.lower():
        return url
    try:
        resp = requests.get(
            url,
            headers=BILIBILI_HEADERS,
            allow_redirects=True,
            timeout=timeout
        )
        if resp.url and "bilibili.com" in resp.url:
            return resp.url
    except Exception:
        pass
    return url


def clean_bilibili_url(url: str) -> str:
    """
    Normalizes a Bilibili URL into canonical watch format (https://www.bilibili.com/video/BV...):
    - Resolves b23.tv and bili2233.cn shortlinks via HTTP 302 redirects
    - Converts embedded player links (player.bilibili.com/player.html?bvid=...) to canonical video URLs
    - Normalizes mobile URLs (m.bilibili.com/video/BV...) to standard desktop URLs
    - Normalizes blackboard or html5mobileplayer URLs containing bvid or aid
    - Preserves Bangumi anime episode URLs (/bangumi/play/ep...)
    - Strips tracking query parameters while preserving multi-part video markers (?p=N)
    """
    if not url:
        return url

    # Resolve shortlinks
    resolved = resolve_bilibili_shortlink(url)

    # Extract part parameter if present (?p=2)
    p_match = re.search(r'[?&]p=(\d+)', resolved)
    p_param = p_match.group(1) if p_match else None

    # Check for BV identifier anywhere in the URL (handles /video/BV..., ?bvid=BV..., etc.)
    bv_match = BVID_REGEX.search(resolved)
    if bv_match:
        bvid = bv_match.group(1)
        # Ensure 'BV' prefix has standard casing
        canonical_bvid = "BV" + bvid[2:]
        base = f"https://www.bilibili.com/video/{canonical_bvid}"
        if p_param and p_param != "1":
            return f"{base}?p={p_param}"
        return base

    # Check for AV identifier (handles /video/av123..., ?aid=123..., etc.)
    av_match = AVID_REGEX.search(resolved)
    if av_match:
        avid = av_match.group(1)
        base = f"https://www.bilibili.com/video/av{avid}"
        if p_param and p_param != "1":
            return f"{base}?p={p_param}"
        return base

    # Bangumi anime link
    bangumi_match = BILIBILI_BANGUMI_REGEX.search(resolved)
    if bangumi_match:
        ep_or_ss = bangumi_match.group(1)
        return f"https://www.bilibili.com/bangumi/play/{ep_or_ss}"

    # General Bilibili link: remove known tracking params
    parsed = urllib.parse.urlparse(resolved)
    query_params = urllib.parse.parse_qs(parsed.query)
    filtered_query = {
        k: v for k, v in query_params.items()
        if k not in (
            "spm_id_from", "vd_source", "share_source", "share_medium",
            "share_plat", "share_session_id", "share_tag", "unique_k",
            "bbid", "ts", "buvid", "from_spmid", "plat_id", "is_story_h5"
        )
    }
    new_query = urllib.parse.urlencode(filtered_query, doseq=True)
    return urllib.parse.urlunparse((parsed.scheme or "https", parsed.netloc, parsed.path, "", new_query, ""))
