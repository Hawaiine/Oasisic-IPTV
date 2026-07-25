# coding: utf-8
"""Tests for lib/clean.py."""

from lib.clean import clean_channel_name


class TestCleanChannelName:
    def test_plain_name(self):
        assert clean_channel_name("CCTV-1") == "CCTV-1"

    def test_strip_resolution(self):
        assert clean_channel_name("CCTV-1 [1080P]") == "CCTV-1"

    def test_strip_resolution_parens(self):
        assert clean_channel_name("湖南卫视(HD)") == "湖南卫视"

    def test_strip_status_marker(self):
        assert clean_channel_name("CCTV-1 [失效]") == "CCTV-1"

    def test_strip_icon_tag(self):
        assert clean_channel_name("CCTV-1 [icon]") == "CCTV-1"

    def test_cctv_normalise(self):
        assert clean_channel_name("CCTV1综合") == "CCTV-1综合"

    def test_cctv_normalise_with_space(self):
        assert clean_channel_name("CCTV 1 综合") == "CCTV-1 综合"

    def test_traditional_to_simplified(self):
        result = clean_channel_name("鳳凰衛視")
        assert result == "凤凰卫视"

    def test_empty_returns_none(self):
        assert clean_channel_name("") is None

    def test_junk_ua_line_returns_none(self):
        assert clean_channel_name("Mozilla/5.0 ...") is None

    def test_junk_comment_line_returns_none(self):
        assert clean_channel_name("#EXTM3U") is None

    def test_short_garbage_returns_none(self):
        assert clean_channel_name("a") is None

    def test_multiple_tags(self):
        assert clean_channel_name("[HD] CCTV-1 [1080P] 综合") == "CCTV-1 综合"

    def test_leading_trailing_dash(self):
        assert clean_channel_name("—CCTV-1—") == "CCTV-1"

    def test_leading_comma(self):
        assert clean_channel_name("，CCTV-1") == "CCTV-1"