"""
Unit tests for Bilibili detection, cleaning, extraction, and header handling.
"""

import unittest
from core.bilibili import is_bilibili_url, clean_bilibili_url, BILIBILI_HEADERS
from core.url_parser import extract_urls_from_text, clean_video_url
from core.scraper import detect_and_resolve_media


class TestBilibili(unittest.TestCase):

    def test_is_bilibili_url(self):
        self.assertTrue(is_bilibili_url("https://www.bilibili.com/video/BV1xx411c7mD"))
        self.assertTrue(is_bilibili_url("http://m.bilibili.com/video/av123456"))
        self.assertTrue(is_bilibili_url("https://b23.tv/abcXYZ1"))
        self.assertTrue(is_bilibili_url("https://bili2233.cn/foo"))
        self.assertTrue(is_bilibili_url("https://player.bilibili.com/player.html?bvid=BV1xx411c7mD"))
        self.assertTrue(is_bilibili_url("https://www.bilibili.tv/en/video/12345"))
        self.assertFalse(is_bilibili_url("https://www.youtube.com/watch?v=dQw4w9WgXcQ"))
        self.assertFalse(is_bilibili_url("https://open.spotify.com/track/4cOdK2wGLETKBW3PvgPWqT"))

    def test_clean_bilibili_url(self):
        raw = "https://www.bilibili.com/video/BV1xx411c7mD?spm_id_from=333.1007.0.0&vd_source=abc1234"
        cleaned = clean_bilibili_url(raw)
        self.assertEqual(cleaned, "https://www.bilibili.com/video/BV1xx411c7mD")

        # Multi-part preserving (?p=2)
        multi = "https://www.bilibili.com/video/BV1xx411c7mD?p=2&spm_id_from=333"
        self.assertEqual(clean_bilibili_url(multi), "https://www.bilibili.com/video/BV1xx411c7mD?p=2")

        # Part 1 stripped to base
        p1 = "https://www.bilibili.com/video/BV1xx411c7mD?p=1"
        self.assertEqual(clean_bilibili_url(p1), "https://www.bilibili.com/video/BV1xx411c7mD")

    def test_clean_player_embed_and_mobile_urls(self):
        # player.bilibili.com with bvid (prevents .html extraction crashes)
        player_bvid = "https://player.bilibili.com/player.html?bvid=BV1xx411c7mD&cid=12345&page=1"
        self.assertEqual(clean_bilibili_url(player_bvid), "https://www.bilibili.com/video/BV1xx411c7mD")

        # player.bilibili.com with aid
        player_aid = "https://player.bilibili.com/player.html?aid=10915022&cid=12345"
        self.assertEqual(clean_bilibili_url(player_aid), "https://www.bilibili.com/video/av10915022")

        # m.bilibili.com mobile link
        m_link = "https://m.bilibili.com/video/BV1xx411c7mD"
        self.assertEqual(clean_bilibili_url(m_link), "https://www.bilibili.com/video/BV1xx411c7mD")

        # blackboard html5 player link
        bb_link = "https://www.bilibili.com/blackboard/html5mobileplayer.html?bvid=BV1xx411c7mD"
        self.assertEqual(clean_bilibili_url(bb_link), "https://www.bilibili.com/video/BV1xx411c7mD")

    def test_extract_from_share_text(self):
        share_text = "【超强AI工具】 https://www.bilibili.com/video/BV1xx411c7mD?spm_id_from=333 复制打开"
        extracted = extract_urls_from_text(share_text)
        self.assertEqual(len(extracted), 1)
        self.assertEqual(extracted[0], "https://www.bilibili.com/video/BV1xx411c7mD?spm_id_from=333")
        cleaned = clean_video_url(extracted[0])
        self.assertEqual(cleaned, "https://www.bilibili.com/video/BV1xx411c7mD")

    def test_clean_video_url_hook(self):
        raw = "https://www.bilibili.com/video/BV1xx411c7mD?spm_id_from=333"
        self.assertEqual(clean_video_url(raw), "https://www.bilibili.com/video/BV1xx411c7mD")

        player_raw = "https://player.bilibili.com/player.html?bvid=BV1xx411c7mD"
        self.assertEqual(clean_video_url(player_raw), "https://www.bilibili.com/video/BV1xx411c7mD")

    def test_headers_structure(self):
        self.assertIn("Referer", BILIBILI_HEADERS)
        self.assertEqual(BILIBILI_HEADERS["Referer"], "https://www.bilibili.com/")
        self.assertIn("User-Agent", BILIBILI_HEADERS)


if __name__ == "__main__":
    unittest.main()
