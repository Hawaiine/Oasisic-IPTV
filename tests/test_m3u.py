# coding: utf-8
"""Tests for lib/m3u.py."""

import os
import tempfile

from lib.m3u import count_extinf, generate_m3u, parse_m3u_content


class TestParseM3uContent:
    def test_parse_basic(self):
        text = """#EXTM3U
#EXTINF:-1 tvg-id="CCTV1" group-title="央视",CCTV-1 综合
http://example.com/cctv1.m3u8
"""
        channels = parse_m3u_content(text, "test")
        assert len(channels) == 1
        assert channels[0]["name"] == "CCTV-1 综合"
        assert channels[0]["url"] == "http://example.com/cctv1.m3u8"
        assert channels[0]["tvg_id"] == "CCTV1"
        assert channels[0]["group_title"] == "央视"

    def test_parse_multiple(self):
        text = """#EXTM3U
#EXTINF:-1 tvg-id="CCTV1",CCTV-1
http://a.com/1.m3u8
#EXTINF:-1 tvg-id="CCTV2",CCTV-2
http://a.com/2.m3u8
"""
        channels = parse_m3u_content(text, "test")
        assert len(channels) == 2

    def test_parse_skip_empty_lines(self):
        text = """#EXTM3U

#EXTINF:-1,CCTV-1
http://a.com/1.m3u8
"""
        channels = parse_m3u_content(text, "test")
        assert len(channels) == 1

    def test_parse_with_tvg_logo(self):
        text = """#EXTM3U
#EXTINF:-1 tvg-id="CCTV1" tvg-logo="http://logo.com/cctv1.png",CCTV-1
http://a.com/1.m3u8
"""
        channels = parse_m3u_content(text, "test")
        assert channels[0]["tvg_logo"] == "http://logo.com/cctv1.png"

    def test_parse_extgrp(self):
        text = """#EXTM3U
#EXTINF:-1,CCTV-1
#EXTGRP:央视
http://a.com/1.m3u8
"""
        channels = parse_m3u_content(text, "test")
        assert channels[0]["group_title"] == "央视"


class TestGenerateM3u:
    def test_generate_and_count(self):
        channels = [
            {"name": "CCTV-1", "url": "http://a.com/1.m3u8", "tvg_id": "CCTV1",
             "tvg_logo": "", "group_title": "央视"},
            {"name": "CCTV-2", "url": "http://a.com/2.m3u8", "tvg_id": "CCTV2",
             "tvg_logo": "", "group_title": "央视"},
        ]
        with tempfile.NamedTemporaryFile(mode="w", suffix=".m3u", delete=False) as f:
            tmp_path = f.name

        try:
            generate_m3u(channels, tmp_path, "Test")
            assert count_extinf(tmp_path) == 2
        finally:
            os.unlink(tmp_path)

    def test_generate_empty(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".m3u", delete=False) as f:
            tmp_path = f.name
        try:
            generate_m3u([], tmp_path)
            assert count_extinf(tmp_path) == 0
        finally:
            os.unlink(tmp_path)


class TestCountExtinf:
    def test_count_nonexistent_file(self):
        assert count_extinf("/nonexistent/path.m3u") == 0

    def test_count_from_fixture(self):
        fixture = os.path.join(
            os.path.dirname(__file__), "fixtures", "sample.m3u"
        )
        assert count_extinf(fixture) == 10