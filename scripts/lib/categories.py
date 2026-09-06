"""中文分组：央视 → 卫视 → 省市 → 港澳台 → 体育 → 直播 → 国际 → 酒店 → 其他。

电台独立文件，不进入主列表。禁止用 iptv-org 国家树/英文类名当主 group-title。
"""

from __future__ import annotations

from collections.abc import Iterator

RADIO_KEY = "radio"

# key -> (中文 group-title, 输出文件后缀)
CATEGORIES: dict[str, tuple[str, str]] = {
    "cctv": ("央视", "cctv"),
    "weishi": ("卫视", "weishi"),
    "local": ("各省市", "local"),
    "gangtai": ("港澳台", "gangtai"),
    "sports": ("体育", "sports"),
    "live": ("网络直播", "live"),
    "overseas": ("国际", "overseas"),
    "hotel": ("酒店", "special"),
    "radio": ("电台", "radio"),
    "other": ("其他", "other"),
}

_MAIN_ORDER = (
    "cctv",
    "weishi",
    "local",
    "gangtai",
    "sports",
    "live",
    "overseas",
    "hotel",
    "other",
)


def group_title(category: str) -> str:
    """返回标准化中文 group-title。未知分类归「其他」。"""
    info = CATEGORIES.get(category)
    return info[0] if info else CATEGORIES["other"][0]


def file_suffix(category: str) -> str:
    info = CATEGORIES.get(category)
    return info[1] if info else "other"


def iter_main_order() -> Iterator[str]:
    """主列表分类顺序（不含电台）。"""
    yield from _MAIN_ORDER


def is_known(category: str) -> bool:
    return category in CATEGORIES
