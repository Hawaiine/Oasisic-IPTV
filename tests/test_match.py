# coding: utf-8
"""Tests for lib/match.py."""

import os

from lib.match import match_channel, reload_tables


class TestMatchChannel:
    def setup_method(self):
        reload_tables()

    def test_match_exact_standard_name(self):
        result = match_channel("CCTV-1")
        assert result is not None
        assert result["standard_name"] == "CCTV-1"
        assert result["category"] == "cctv"

    def test_match_via_alias(self):
        result = match_channel("CCTV1")
        assert result is not None
        assert result["standard_name"] == "CCTV-1"

    def test_match_another_alias(self):
        result = match_channel("湖南台")
        assert result is not None
        assert result["standard_name"] == "湖南卫视"

    def test_match_hunan_tv_direct(self):
        result = match_channel("湖南卫视")
        assert result is not None
        assert result["tvg_id"] == "HunanTV"

    def test_match_fenghuang(self):
        result = match_channel("凤凰卫视")
        assert result is not None
        assert result["standard_name"] == "凤凰卫视中文台"

    def test_match_nonexistent(self):
        result = match_channel("这个频道不存在")
        assert result is None

    def test_match_empty(self):
        assert match_channel("") is None

    def test_match_whitespace(self):
        assert match_channel("   ") is None

    def test_match_tvb(self):
        result = match_channel("TVB")
        assert result is not None
        assert result["standard_name"] == "TVB Jade"

    def test_match_returns_copy_not_reference(self):
        result = match_channel("CCTV-1")
        result["standard_name"] = "MODIFIED"
        # Re-check that original is unchanged
        result2 = match_channel("CCTV-1")
        assert result2["standard_name"] == "CCTV-1"