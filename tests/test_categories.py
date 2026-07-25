# coding: utf-8
"""Tests for lib/categories.py."""

from lib.categories import (
    RADIO_KEY,
    all_categories,
    file_for,
    group_title,
    is_radio,
    iter_main_order,
    title_for,
)


class TestCategories:
    def test_iter_main_order_has_expected_first_and_last(self):
        order = list(iter_main_order())
        assert order[0] == "cctv"
        assert order[-1] == "other"

    def test_iter_main_order_excludes_radio(self):
        assert RADIO_KEY not in list(iter_main_order())

    def test_all_categories_includes_radio(self):
        cats = all_categories()
        assert RADIO_KEY in cats

    def test_file_for_cctv(self):
        assert file_for("cctv") == "live_cctv.m3u"

    def test_file_for_radio(self):
        assert file_for("radio") == "live_radio.m3u"

    def test_file_for_weishi(self):
        assert file_for("weishi") == "live_weishi.m3u"

    def test_title_for_cctv(self):
        assert title_for("cctv") == "央视"

    def test_title_for_overseas(self):
        assert title_for("overseas") == "国际"

    def test_group_title_matches_title(self):
        assert group_title("cctv") == title_for("cctv")

    def test_is_radio_positive(self):
        assert is_radio("radio") is True

    def test_is_radio_negative(self):
        assert is_radio("cctv") is False

    def test_radio_key_constant(self):
        assert RADIO_KEY == "radio"