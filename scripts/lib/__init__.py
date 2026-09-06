"""Oasisic-IPTV 核心库。"""

from .io_util import project_root, load_yaml, load_json, save_json, save_text
from .categories import CATEGORIES, group_title, iter_main_order, RADIO_KEY

__all__ = [
    "project_root",
    "load_yaml",
    "load_json",
    "save_json",
    "save_text",
    "CATEGORIES",
    "group_title",
    "iter_main_order",
    "RADIO_KEY",
]
