# coding: utf-8
"""
Channel name cleaning utilities.

Functions
---------
clean_channel_name(raw: str) -> str | None
    Normalise a channel name: strip resolution tags, status markers,
    icon artefacts, normalise CCTV variants, convert traditional→simplified
    Chinese, and discard junk UA lines.
"""

from __future__ import annotations

import re

import zhconv

# ── Regex patterns ─────────────────────────────────────────────────

# Resolution / quality tags (e.g. [1080P], (HD), 4K, UHD, FHD)
_RES_TAG = re.compile(
    r"""
    [\[\(]?\s*
    ( \d{3,4}[pPiI]       # 1080P, 720p, 432P
    | 4K | UHD | FHD | HD | SD
    | 超清[普标]?  | 高清[普标]?  | 标清[普标]?
    | 极清 | 蓝光 | 流畅
    )
    \s*[\]\)]?
    """,
    re.IGNORECASE | re.VERBOSE,
)

# Status / source markers
_STATUS_TAG = re.compile(
    r"""
    \[?\s*
    ( 失效 | 备用 | 官方 | 测试 | 主用 | 唯一
    | 电信 | 联通 | 移动 | 广电
    | 中国 | 默认
    | \d+M
    | Not\s*24/7 | geo[- ]?block | geo[- ]?restrict
    )
    \s*\]?
    """,
    re.IGNORECASE | re.VERBOSE,
)

# Icon artefacts like [file] [icon] [logo] at the end
_ICON_TAG = re.compile(r"\[(?:file|icon|logo|img)\]", re.IGNORECASE)

# Junk / garbage lines (UA strings, empty lines after cleaning)
_JUNK_LINE = re.compile(
    r"^[#\s]*$"
    r"|^Mozilla/"
    r"|^User-Agent"
    r"|^#(?:EXTM3U|EXTINF|EXTVLCOPT|KODIPROP)",
    re.IGNORECASE,
)

# CCTV normalisation: "CCTV 1 综合" -> "CCTV-1 综合", "CCTV1" -> "CCTV-1"
_CCTV_FIX = re.compile(r"\bCCTV\s*(\d+)((?:\s*[-—]\s*)?)", re.IGNORECASE)
_CCTV_FULL = re.compile(r"\b(中国中央电视台)\s*[-—]?\s*(\d+)?", re.IGNORECASE)

# Empty parens left over after removing (HD) etc.
_EMPTY_PARENS = re.compile(r"\(\s*\)|\[\s*\]")

# Multiple consecutive spaces
_MULTI_SPACE = re.compile(r" {2,}")

# Leading/trailing noise
_LEADING_DASH = re.compile(r"^[—\-–\s,，、]+")
_TRAILING_JUNK = re.compile(r"[—\-–\s,，、]+$")


def clean_channel_name(raw: str) -> str | None:
    """
    Clean a raw channel name.

    Steps
    -----
    1. Strip whitespace
    2. Remove resolution tags
    3. Remove status / source markers
    4. Remove icon artefacts
    5. Normalise CCTV variants to ``CCTV-N``
    6. Convert traditional Chinese to simplified
    7. Strip leading/trailing punctuation
    8. Return None if the result is empty or junk

    Parameters
    ----------
    raw : str
        Raw channel name from an M3U entry.

    Returns
    -------
    str | None
        Cleaned name, or None if the line should be discarded.
    """
    name = raw.strip()

    # Reject junk lines early
    if _JUNK_LINE.match(name):
        return None

    # Remove resolution/quality tags
    name = _RES_TAG.sub("", name).strip()

    # Remove status/source markers
    name = _STATUS_TAG.sub("", name).strip()

    # Remove icon artefacts
    name = _ICON_TAG.sub("", name).strip()

    # Normalise CCTV patterns
    # "CCTV 1 综合" -> "CCTV-1 综合" (keep the program name)
    name = _CCTV_FIX.sub(r"CCTV-\1\2", name)
    # "中国中央电视台" -> "CCTV"
    name = _CCTV_FULL.sub(r"CCTV", name)
    # Remove stray dash after CCTV when no number follows
    name = re.sub(r"\bCCTV-\s*$", "CCTV", name)

    # Remove empty parens left from tag removal
    name = _EMPTY_PARENS.sub("", name).strip()

    # Collapse multiple spaces
    name = _MULTI_SPACE.sub(" ", name)

    # Traditional → Simplified Chinese
    name = zhconv.convert(name, "zh-cn")

    # Strip leading/trailing punctuation
    name = _LEADING_DASH.sub("", name)
    name = _TRAILING_JUNK.sub("", name)

    name = name.strip()

    # Discard if empty or still looks like junk
    if not name or len(name) < 2:
        return None

    return name