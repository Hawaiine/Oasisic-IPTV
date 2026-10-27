"""广告/占位源识别单测。"""

from __future__ import annotations

from lib.adfilter import detect_placeholder, is_placeholder_name, playlist_is_ad, playlist_is_placeholder

SHORT_LOOP = """#EXTM3U
#EXT-X-VERSION:3
#EXTINF:5.0,
https://example.com/ad/1.ts
#EXTINF:5.0,
https://example.com/ad/2.ts
#EXT-X-ENDLIST
"""

LONG_PLAYLIST = """#EXTM3U
#EXT-X-VERSION:3
#EXTINF:10.0,
https://example.com/live/1.ts
#EXTINF:10.0,
https://example.com/live/2.ts
#EXTINF:10.0,
https://example.com/live/3.ts
#EXTINF:10.0,
https://example.com/live/4.ts
#EXTINF:10.0,
https://example.com/live/5.ts
#EXTINF:10.0,
https://example.com/live/6.ts
#EXTINF:10.0,
https://example.com/live/7.ts
"""


def test_placeholder_names() -> None:
    for name in ("CCTV-1 无信号", "测试卡", "彩条信号", "敬请期待", "广告位1"):
        assert is_placeholder_name(name), name
    for name in ("CCTV-1 综合", "湖南卫视", "武汉新闻综合", "凤凰卫视资讯台"):
        assert not is_placeholder_name(name), name


def test_short_endlist_loop_is_placeholder() -> None:
    assert playlist_is_placeholder(SHORT_LOOP)
    assert not playlist_is_placeholder(LONG_PLAYLIST)


def test_ad_segments_detected() -> None:
    assert playlist_is_ad(SHORT_LOOP)
    ad_text = "#EXTM3U\n#EXTINF:10,\nhttps://x/guanggao/1.ts\n"
    assert playlist_is_ad(ad_text)


def test_detect_placeholder_precedence() -> None:
    assert detect_placeholder(SHORT_LOOP) == "placeholder"
    assert detect_placeholder("https://x/y.m3u8?u=/ads/1.ts") == "ad"
    assert detect_placeholder(LONG_PLAYLIST) is None
