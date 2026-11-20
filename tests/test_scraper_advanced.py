"""
Unit tests for Advanced Universal Media Scraper and Resilient Extractors.
Tests:
- Dean Edwards P.A.C.K.E.R. unpacker
- Schema.org JSON-LD VideoObject extraction
- Next.js __NEXT_DATA__ video stream extraction
- Twitter/X syndication fallback
- Anti-hotlinking headers injection
- Browser cookie fallback resilience
"""

import unittest
from unittest.mock import patch, MagicMock
from core.scraper import (
    unpack_dean_edwards_packer,
    detect_and_resolve_media,
    fetch_twitter_video_fallback,
    BROWSER_HEADERS
)
from core.downloader import AudioDownloader


class AdvancedScraperTests(unittest.TestCase):

    def test_unpack_dean_edwards_packer(self):
        # Sample 1: Standard P.A.C.K.E.R.
        sample1 = (
            "eval(function(p,a,c,k,e,d){while(c--)if(k[c])p=p.replace("
            "new RegExp('\\\\b'+c.toString(a)+'\\\\b','g'),k[c]);return p}"
            "('0 1=\"2://3.4/5.6\";',7,7,'var|source|https|cdn|example|stream|m3u8'.split('|')))"
        )
        unpacked1 = unpack_dean_edwards_packer(sample1)
        self.assertIn("https://cdn.example/stream.m3u8", unpacked1)
        self.assertIn("var source=", unpacked1)

        # Sample 2: P.A.C.K.E.R. with radix 36 and closing objects
        sample2 = (
            "eval(function(p,a,c,k,e,d){e=function(c){return c.toString(36)};"
            "while(c--){if(k[c]){p=p.replace(new RegExp('\\\\b'+e(c)+'\\\\b','g'),k[c])}}"
            "return p}('4 5={\"1\":\"0://2.3/6.7\"};',8,8,'https|file|video|cdn|var|player|master|mpd'.split('|'),0,{}))"
        )
        unpacked2 = unpack_dean_edwards_packer(sample2)
        self.assertIn("https://video.cdn/master.mpd", unpacked2)
        self.assertIn("var player=", unpacked2)

    @patch("core.scraper.fetch_page_content")
    def test_jsonld_video_object_extraction(self, mock_fetch):
        html_payload = """
        <!DOCTYPE html>
        <html>
        <head>
          <title>News Story Title</title>
          <script type="application/ld+json">
          {
            "@context": "https://schema.org",
            "@type": "VideoObject",
            "name": "Live Spacecraft Docking Event",
            "description": "Footage of the orbital docking",
            "thumbnailUrl": "https://example.com/thumb.jpg",
            "contentUrl": "https://cdn.example.com/videos/docking_1080p.mp4"
          }
          </script>
        </head>
        <body><p>News Content</p></body>
        </html>
        """
        mock_fetch.return_value = (200, html_payload, {"content-type": "text/html; charset=utf-8"})

        result = detect_and_resolve_media("https://news.example.com/article/12345")
        self.assertEqual(result["media_type"], "video")
        self.assertEqual(result["title"], "Live Spacecraft Docking Event")
        self.assertEqual(result["stream_url"], "https://cdn.example.com/videos/docking_1080p.mp4")
        self.assertEqual(result["thumbnail_url"], "https://example.com/thumb.jpg")
        self.assertEqual(result["http_headers"]["Referer"], "https://news.example.com/article/12345")
        self.assertEqual(result["http_headers"]["Origin"], "https://news.example.com")

    @patch("core.scraper.fetch_page_content")
    def test_nextjs_hydration_stream_extraction(self, mock_fetch):
        html_payload = """
        <!DOCTYPE html>
        <html>
        <head>
          <title>Next.js Media Stream</title>
        </head>
        <body>
          <script id="__NEXT_DATA__" type="application/json">
          {
            "props": {
              "pageProps": {
                "video": {
                  "id": "abc123xyz",
                  "playbackUrl": "https:\\/\\/streaming.example.org\\/live\\/master.m3u8",
                  "title": "Next.js Exclusive Stream"
                }
              }
            }
          }
          </script>
        </body>
        </html>
        """
        mock_fetch.return_value = (200, html_payload, {"content-type": "text/html"})

        result = detect_and_resolve_media("https://streaming.example.org/watch/abc123xyz")
        self.assertEqual(result["media_type"], "video")
        self.assertEqual(result["stream_url"], "https://streaming.example.org/live/master.m3u8")
        self.assertEqual(result["http_headers"]["Referer"], "https://streaming.example.org/watch/abc123xyz")
        self.assertEqual(result["http_headers"]["Origin"], "https://streaming.example.org")

    @patch("core.scraper.fetch_page_content")
    def test_packed_javascript_embedded_stream_extraction(self, mock_fetch):
        # Emulates video platforms using packed JS to hide .m3u8 stream manifests
        packed_script = (
            "eval(function(p,a,c,k,e,d){while(c--)if(k[c])p=p.replace("
            "new RegExp('\\\\b'+c.toString(a)+'\\\\b','g'),k[c]);return p}"
            "('0 1={2:\"3://4.5/6/7.8\"};',9,9,'var|playerConfig|file|https|hls|streamhub|vod|video|m3u8'.split('|')))"
        )
        html_payload = f"""
        <!DOCTYPE html>
        <html>
        <head><title>Obfuscated Stream Player</title></head>
        <body>
          <script>
          {packed_script}
          </script>
        </body>
        </html>
        """
        mock_fetch.return_value = (200, html_payload, {"content-type": "text/html"})

        result = detect_and_resolve_media("https://streamhub.net/v/999")
        self.assertEqual(result["media_type"], "video")
        self.assertEqual(result["stream_url"], "https://hls.streamhub/vod/video.m3u8")

    @patch("core.scraper.fetch_page_content")
    def test_twitter_syndication_fallback(self, mock_fetch):
        tweet_json = {
            "text": "Check out this incredible high-speed launch footage from earlier today!",
            "user_name": "SpaceExplorer",
            "video_url": "https://video.twimg.com/ext_tw_video/12345/pu/vid/avc1/1280x720/launch.mp4",
            "media_thumb_url": "https://pbs.twimg.com/media/thumb123.jpg"
        }
        import json
        mock_fetch.return_value = (200, json.dumps(tweet_json), {"content-type": "application/json"})

        fb = fetch_twitter_video_fallback("https://x.com/SpaceExplorer/status/1234567890123456789")
        self.assertIsNotNone(fb)
        self.assertEqual(fb["platform"], "Twitter / X")
        self.assertEqual(fb["stream_url"], "https://video.twimg.com/ext_tw_video/12345/pu/vid/avc1/1280x720/launch.mp4")
        self.assertEqual(fb["http_headers"]["Referer"], "https://x.com/")

    def test_cookie_resilience_fallback(self):
        downloader = AudioDownloader(browser_cookies="chrome")
        # Simulates yt-dlp raising a DPAPI decryption error during cookie extraction
        mock_action = MagicMock()
        mock_action.side_effect = [
            RuntimeError("Failed to decrypt with DPAPI. See issue 10927"),
            {"id": "test_vid", "title": "Fallback Success"}
        ]
        opts = {"cookiesfrombrowser": ("chrome",), "quiet": True}
        res = downloader._execute_ydl(opts, mock_action)
        self.assertEqual(res["title"], "Fallback Success")
        self.assertEqual(mock_action.call_count, 2)

    @patch("core.scraper.fetch_page_content")
    def test_steam_multi_trailer_collection(self, mock_fetch):
        import json
        steam_payload = {
            "730": {
                "success": True,
                "data": {
                    "name": "Counter-Strike 2",
                    "header_image": "https://cdn.example.com/header.jpg",
                    "movies": [
                        {
                            "id": 1,
                            "name": "Launch Trailer",
                            "thumbnail": "https://cdn.example.com/thumb1.jpg",
                            "hls_h264": "https://cdn.example.com/trailer1.m3u8"
                        },
                        {
                            "id": 2,
                            "name": "Gameplay Trailer",
                            "thumbnail": "https://cdn.example.com/thumb2.jpg",
                            "hls_h264": "https://cdn.example.com/trailer2.m3u8"
                        },
                        {
                            "id": 3,
                            "name": "Features Teaser",
                            "thumbnail": "https://cdn.example.com/thumb3.jpg",
                            "hls_h264": "https://cdn.example.com/trailer3.m3u8"
                        }
                    ]
                }
            }
        }
        mock_fetch.return_value = (200, json.dumps(steam_payload), {"content-type": "application/json"})

        res = detect_and_resolve_media("https://store.steampowered.com/app/730/CounterStrike_2/")
        self.assertEqual(res["platform"], "Steam")
        self.assertEqual(res["media_type"], "collection")
        self.assertTrue(res["is_collection"])
        self.assertEqual(res["collection_count"], 3)
        self.assertEqual(len(res["entries"]), 3)
        self.assertEqual(res["entries"][0]["title"], "Counter-Strike 2 - Launch Trailer")
        self.assertEqual(res["entries"][0]["stream_url"], "https://cdn.example.com/trailer1.m3u8")
        self.assertEqual(res["entries"][1]["title"], "Counter-Strike 2 - Gameplay Trailer")
        self.assertEqual(res["entries"][2]["title"], "Counter-Strike 2 - Features Teaser")


if __name__ == "__main__":
    unittest.main()
