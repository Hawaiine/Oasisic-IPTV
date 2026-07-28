# coding: utf-8
"""Tests for collect.py: _select_best global dedup logic."""

import sys
import os

# Ensure scripts/ is importable
_SCRIPTS = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "scripts"))
if _SCRIPTS not in sys.path:
    sys.path.insert(0, _SCRIPTS)

from collect import _select_best, _SOURCE_PRIORITY


def _make_ch(name, url, cat="cctv", region="cn", standard_name=""):
    """Helper to build a channel dict."""
    return {
        "name": name,
        "url": url,
        "category": cat,
        "source_region": region,
        "standard_name": standard_name or name,
        "alive": True,
        "latency_ms": 999999,
    }


class TestGlobalDedup:
    """Verify _select_best enforces max_keep globally across categories."""

    def test_same_name_across_categories_deduped(self):
        """Same standard_name in 'cctv' and 'other' → only max_keep=2 kept."""
        groups = {
            "cctv": [
                _make_ch("CCTV-1", "http://a.com/1", "cctv", "cn", "CCTV-1"),
                _make_ch("CCTV-1", "http://a.com/2", "cctv", "cn", "CCTV-1"),
            ],
            "other": [
                _make_ch("CCTV-1", "http://a.com/3", "other", "cn", "CCTV-1"),
                _make_ch("CCTV-1", "http://a.com/4", "other", "cn", "CCTV-1"),
            ],
        }
        result = _select_best(groups, 2)
        total = sum(len(v) for v in result.values())
        # 4 entries, max_keep=2 → only 2 kept globally
        assert total == 2, f"expected 2, got {total}"
        # Check that cn priority entries are kept
        urls = []
        for ch_list in result.values():
            for ch in ch_list:
                urls.append(ch["url"])
        assert "http://a.com/1" in urls
        assert "http://a.com/2" in urls

    def test_same_url_deduped(self):
        """Same URL within a category → only one copy."""
        groups = {
            "cctv": [
                _make_ch("CCTV-1", "http://a.com/1", "cctv", "cn", "CCTV-1"),
                _make_ch("CCTV-1", "http://a.com/1", "cctv", "cn", "CCTV-1"),
            ],
        }
        result = _select_best(groups, 2)
        total = sum(len(v) for v in result.values())
        assert total == 1, f"expected 1 (URL dedup), got {total}"

    def test_source_priority_ordering(self):
        """cn sources preferred over overseas when both have same name."""
        groups = {
            "cctv": [
                _make_ch("CCTV-1", "http://cn/1", "cctv", "cn", "CCTV-1"),
                _make_ch("CCTV-1", "http://overseas/1", "cctv", "overseas", "CCTV-1"),
            ],
        }
        result = _select_best(groups, 2)
        total = sum(len(v) for v in result.values())
        assert total == 2, f"expected 2 (both regions, max_keep=2), got {total}"

    def test_radio_isolated(self):
        """Radio category should not be merged into main."""
        groups = {
            "cctv": [
                _make_ch("CCTV-1", "http://a.com/1", "cctv", "cn", "CCTV-1"),
            ],
            "radio": [
                _make_ch("Radio 1", "http://radio/1", "radio", "cn", "Radio 1"),
            ],
        }
        result = _select_best(groups, 2)
        assert "radio" in result
        assert len(result["radio"]) == 1
        # Radio should not be touched by global dedup
        assert result["radio"][0]["name"] == "Radio 1"

    def test_same_url_different_name_deduped(self):
        """Same URL used by different names → only one entry kept."""
        groups = {
            "cctv": [
                _make_ch("CCTV-1", "http://same.url/1", "cctv", "cn", "CCTV-1"),
                _make_ch("CCTV-2", "http://same.url/1", "cctv", "cn", "CCTV-2"),
            ],
        }
        result = _select_best(groups, 2)
        total = sum(len(v) for v in result.values())
        assert total == 1, f"expected 1 (URL dedup), got {total}"

    def test_same_url_cn_over_overseas(self):
        """Same URL, cn vs overseas → keep cn."""
        groups = {
            "cctv": [
                _make_ch("CCTV-1", "http://same.url/1", "cctv", "cn", "CCTV-1"),
            ],
            "overseas": [
                _make_ch("CCTV-1", "http://same.url/1", "overseas", "overseas", "CCTV-1"),
            ],
        }
        result = _select_best(groups, 2)
        total = sum(len(v) for v in result.values())
        assert total == 1, f"expected 1, got {total}"
        for ch_list in result.values():
            for ch in ch_list:
                assert ch["source_region"] == "cn", f"expected cn, got {ch['source_region']}"

    def test_same_url_radio_loses_to_non_radio(self):
        """Same URL shared by radio and non-radio → non-radio wins."""
        groups = {
            "cctv": [
                _make_ch("CCTV-1", "http://same.url/1", "cctv", "cn", "CCTV-1"),
            ],
            "radio": [
                _make_ch("Radio 1", "http://same.url/1", "radio", "cn", "Radio 1"),
            ],
        }
        result = _select_best(groups, 2)
        total = sum(len(v) for v in result.values())
        assert total == 1, f"expected 1 (radio drops URL), got {total}"
        assert "cctv" in result
        assert len(result["cctv"]) == 1

    def test_rtp_penalty_max_keep_1(self):
        """rtp:// loses to http:// when max_keep=1."""
        groups = {
            "cctv": [
                _make_ch("CCTV-1", "http://normal/1", "cctv", "cn", "CCTV-1"),
                _make_ch("CCTV-1", "rtp://239.1.1.1:1234", "cctv", "cn", "CCTV-1"),
            ],
        }
        result = _select_best(groups, 1)
        total = sum(len(v) for v in result.values())
        assert total == 1
        for ch_list in result.values():
            for ch in ch_list:
                assert ch["url"].startswith("http"), f"expected http, got {ch['url']}"

    def test_rtp_penalty_max_keep_2(self):
        """With max_keep=2, rtp:// is kept but comes second."""
        groups = {
            "cctv": [
                _make_ch("CCTV-1", "http://normal/1", "cctv", "cn", "CCTV-1"),
                _make_ch("CCTV-1", "rtp://239.1.1.1:1234", "cctv", "cn", "CCTV-1"),
            ],
        }
        result = _select_best(groups, 2)
        total = sum(len(v) for v in result.values())
        assert total == 2
        # First should be http, second rtp
        for ch_list in result.values():
            ch_list_sorted = sorted(ch_list, key=lambda x: x.get("url", ""))
            assert ch_list_sorted[0]["url"].startswith("http")