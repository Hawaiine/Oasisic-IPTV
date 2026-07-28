# coding: utf-8
"""Tests for D2 catalog/more split logic."""

import sys
import os
import json

_SCRIPTS = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "scripts"))
if _SCRIPTS not in sys.path:
    sys.path.insert(0, _SCRIPTS)

from collect import _split_catalog_more, _select_best, _SOURCE_PRIORITY
from lib import categories as cat


def _make_ch(name, url, cat_key="cctv", region="cn", standard_name=None):
    """Helper to build a channel dict.
    Pass standard_name=None for unmatched channels (will not have standard_name).
    Pass standard_name="name" for matched channels.
    Omitting standard_name (or passing None) means no standard_name.
    """
    # Only set standard_name if explicitly provided (not None)
    # None means "no standard_name" - keep as empty string so _select_best uses name as key
    return {
        "name": name,
        "url": url,
        "category": cat_key,
        "source_region": region,
        "standard_name": standard_name if standard_name is not None else "",
        "alive": True,
        "latency_ms": 999999,
    }


class TestCatalogMoreSplit:
    """Verify catalog/more split logic."""

    def test_standard_name_goes_to_catalog(self):
        """Channels with standard_name → catalog."""
        groups = {
            "cctv": [
                _make_ch("CCTV-1 综合", "http://a.com/1", "cctv", "cn", "CCTV-1"),
            ],
        }
        selected = _select_best(groups, 1)
        catalog, more = _split_catalog_more(selected, main_include_overseas=False)
        catalog_total = sum(len(v) for v in catalog.values())
        assert catalog_total == 1, f"expected 1, got {catalog_total}"
        assert len(more) == 0

    def test_no_standard_name_goes_to_more(self):
        """Channels without standard_name → more."""
        groups = {
            "local": [
                _make_ch("SomeLocalChannel", "http://a.com/2", "local", "cn", standard_name=None),
            ],
        }
        selected = _select_best(groups, 1)
        catalog, more = _split_catalog_more(selected, main_include_overseas=False)
        catalog_total = sum(len(v) for v in catalog.values())
        assert catalog_total == 0, f"expected 0, got {catalog_total}"
        assert len(more) == 1

    def test_live_m3u_catalog_only(self):
        """live.m3u should only contain standard table matched channels."""
        groups = {
            "cctv": [
                _make_ch("CCTV-1 综合", "http://a.com/1", "cctv", "cn", "CCTV-1"),
            ],
            "local": [
                _make_ch("SomeLocal", "http://a.com/2", "local", "cn", standard_name=None),
            ],
        }
        selected = _select_best(groups, 1)
        catalog, more = _split_catalog_more(selected, main_include_overseas=False)
        # Only CCTV-1 should be in catalog
        catalog_total = sum(len(v) for v in catalog.values())
        assert catalog_total == 1
        # SomeLocal should be in more
        assert len(more) == 1

    def test_max_keep_1_enforced_in_catalog(self):
        """Same standard_name → only 1 entry in catalog (max_keep=1)."""
        groups = {
            "cctv": [
                _make_ch("CCTV-1 综合", "http://a.com/1", "cctv", "cn", "CCTV-1"),
                _make_ch("CCTV-1 综合", "http://a.com/2", "cctv", "cn", "CCTV-1"),
            ],
        }
        selected = _select_best(groups, 1)
        catalog, more = _split_catalog_more(selected, main_include_overseas=False)
        catalog_total = sum(len(v) for v in catalog.values())
        assert catalog_total == 1, f"expected 1, got {catalog_total}"

    def test_radio_not_in_more(self):
        """Radio channels should never appear in more."""
        groups = {
            "radio": [
                _make_ch("FM 101", "http://radio.com/1", "radio", "cn", "Radio 101"),
            ],
        }
        selected = _select_best(groups, 1)
        catalog, more = _split_catalog_more(selected, main_include_overseas=False)
        assert len(more) == 0, "radio should not be in more"

    def test_overseas_excluded_from_catalog(self):
        """Overseas should not be in catalog when main_include_overseas=False."""
        groups = {
            "overseas": [
                _make_ch("BBC News", "http://bbc.com", "overseas", "overseas", standard_name=None),
            ],
        }
        selected = _select_best(groups, 1)
        catalog, more = _split_catalog_more(selected, main_include_overseas=False)
        catalog_total = sum(len(v) for v in catalog.values())
        # Overseas category has 0 in catalog
        assert "overseas" not in catalog or len(catalog.get("overseas", [])) == 0

    def test_catalog_entries_have_standard_name(self):
        """All catalog entries must have a standard_name."""
        groups = {
            "cctv": [
                _make_ch("CCTV-1", "http://a.com/1", "cctv", "cn", "CCTV-1"),
                _make_ch("CCTV-2", "http://a.com/2", "cctv", "cn", "CCTV-2"),
            ],
            "local": [
                _make_ch("NoMatch", "http://a.com/3", "local", "cn", standard_name=None),
            ],
        }
        selected = _select_best(groups, 1)
        catalog, _more = _split_catalog_more(selected, main_include_overseas=False)
        for key, ch_list in catalog.items():
            if key == "radio":
                continue
            for ch in ch_list:
                assert ch.get("standard_name"), f"Catalog entry missing standard_name: {ch}"


class TestNewChannelsInTable:
    """Verify that new channels added in D2 are in the channels.json."""

    def test_hebei_weishi_in_table(self):
        chs = json.load(open(os.path.join(os.path.dirname(_SCRIPTS), "data", "channels.json")))
        names = {ch["standard_name"] for ch in chs}
        assert "河北卫视" in names, "河北卫视 missing from channels.json"

    def test_qinghai_weishi_in_table(self):
        chs = json.load(open(os.path.join(os.path.dirname(_SCRIPTS), "data", "channels.json")))
        names = {ch["standard_name"] for ch in chs}
        assert "青海卫视" in names, "青海卫视 missing from channels.json"

    def test_sansha_weishi_in_table(self):
        chs = json.load(open(os.path.join(os.path.dirname(_SCRIPTS), "data", "channels.json")))
        names = {ch["standard_name"] for ch in chs}
        assert "三沙卫视" in names, "三沙卫视 missing from channels.json"

    def test_table_count_at_least_120(self):
        chs = json.load(open(os.path.join(os.path.dirname(_SCRIPTS), "data", "channels.json")))
        assert len(chs) >= 120, f"channels.json has {len(chs)} entries, need ≥120"

    def test_cctv5_in_table(self):
        chs = json.load(open(os.path.join(os.path.dirname(_SCRIPTS), "data", "channels.json")))
        names = {ch["standard_name"] for ch in chs}
        assert "CCTV-5" in names, "CCTV-5 missing from channels.json"
        assert "CCTV-5+" in names, "CCTV-5+ missing from channels.json"

    def test_no_orphan_aliases(self):
        chs = json.load(open(os.path.join(os.path.dirname(_SCRIPTS), "data", "channels.json")))
        als = json.load(open(os.path.join(os.path.dirname(_SCRIPTS), "data", "aliases.json")))
        std_names = {ch["standard_name"] for ch in chs}
        orphans = {k for k, v in als.items() if v not in std_names}
        assert len(orphans) == 0, f"Orphan aliases: {orphans}"