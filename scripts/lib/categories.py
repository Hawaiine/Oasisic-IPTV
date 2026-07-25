# coding: utf-8
"""
Category definitions for Oasisic-IPTV.

Main ordered list (used for M3U group-title and file naming):
    cctv, weishi, local, gangtai, sports, live, overseas, special, other

Radio is kept separate — filename: live_radio.m3u
"""

from __future__ import annotations

import typing as t

# ── Category metadata ──────────────────────────────────────────────

# (category_key, group_title, filename_suffix, description)
_category_defs: list[tuple[str, str, str, str]] = [
    ("cctv",     "央视",   "cctv",     "CCTV channels"),
    ("weishi",   "卫视",   "weishi",   "Satellite TV"),
    ("local",    "各省市", "local",    "Provincial / local channels"),
    ("gangtai",  "港澳台", "gangtai",  "HK / Macau / Taiwan"),
    ("sports",   "体育",   "sports",   "Sports channels"),
    ("live",     "网络直播", "live",    "Live-streaming platforms (Douyu, Huya, Bilibili …)"),
    ("overseas", "国际",   "overseas", "International channels"),
    ("special",  "特殊·酒店源", "special", "Hotel / special sources"),
    ("other",    "其他",   "other",    "Unclassified"),
]

# Radio is deliberately excluded from the main list.
_RADIO: tuple[str, str, str, str] = ("radio", "电台", "radio", "Radio channels")

# ── Lookup maps (built once) ───────────────────────────────────────

_FILE_FOR: dict[str, str] = {}
_TITLE_FOR: dict[str, str] = {}
_GROUP_TITLE: dict[str, str] = {}

for key, title, suffix, _desc in _category_defs:
    _FILE_FOR[key] = f"live_{suffix}.m3u"
    _TITLE_FOR[key] = title
    _GROUP_TITLE[key] = title

# Radio
_file_r, _title_r, _suffix_r, _desc_r = _RADIO
_FILE_FOR[_file_r] = f"live_{_suffix_r}.m3u"
_TITLE_FOR[_file_r] = _title_r
_GROUP_TITLE[_file_r] = _title_r


# ── Public API ─────────────────────────────────────────────────────


def iter_main_order() -> t.Iterator[str]:
    """Yield category keys in the canonical display order (radio excluded)."""
    return (key for key, *_ in _category_defs)


def file_for(cat: str) -> str:
    """Return the m3u filename for a category, e.g. ``live_cctv.m3u``."""
    return _FILE_FOR[cat]


def title_for(cat: str) -> str:
    """Return the human-readable Chinese title for a category."""
    return _TITLE_FOR[cat]


def group_title(cat: str) -> str:
    """Return the M3U ``#EXTGRP`` value for a category."""
    return _GROUP_TITLE[cat]


def all_categories() -> list[str]:
    """Return all category keys including radio."""
    return [key for key, *_ in _category_defs] + [_RADIO[0]]


def is_radio(cat: str) -> bool:
    """Return True if the category is radio."""
    return cat == _RADIO[0]


# ── Convenience ────────────────────────────────────────────────────

RADIO_KEY: str = _RADIO[0]