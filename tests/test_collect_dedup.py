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