"""广告/占位源识别：把"能连上但不是真频道"的源挡在选优之前。

两类噪声：
1. 名字级：`无信号`、`测试卡`、`敬请期待`、`广告` 等（不依赖网络）；
2. 内容级：首片播放列表是广告/占位循环——`#EXT-X-ENDLIST` 且总时长很短，
   或分片地址命中 `ad|ads|gg|guanggao`。

纯函数，无 IO；供 lib/health.grade() 与探测流程复用。
"""

from __future__ import annotations

import re

# 名字级：这些词基本只出现在占位/广告条目上
PLACEHOLDER_NAME_RE = re.compile(
    r"无信号|测试卡|测试图|测试画面|彩条|彩条纹|雪点|敬请期待|广告|广告位|停机公告",
    re.IGNORECASE,
)

_AD_SEGMENT_RE = re.compile(
    r"(?:^|/)(?:ad|ads|advert|advertisement|gg|guanggao)(?:\d|[-_./]|$)",
    re.IGNORECASE,
)
_EXTINF_DUR_RE = re.compile(r"#EXTINF:\s*(-?[0-9.]+)")


def is_placeholder_name(name: str) -> bool:
    """名字本身是不是占位/广告条目。"""
    return bool(PLACEHOLDER_NAME_RE.search((name or "").strip()))


def playlist_is_placeholder(text: str) -> bool:
    """播放列表是不是「马上结束的短循环」——广告/无信号的典型形态。"""
    body = text or ""
    if "#EXT-X-ENDLIST" not in body:
        return False
    durations = [float(d) for d in _EXTINF_DUR_RE.findall(body) if d and d != "-1"]
    if not durations:
        return False
    return sum(durations) < 60


def playlist_is_ad(text: str) -> bool:
    """播放列表里的分片地址是不是清一色广告位。"""
    segments = [ln.strip() for ln in (text or "").splitlines() if ln.strip() and not ln.startswith("#")]
    if not segments:
        return False
    return all(_AD_SEGMENT_RE.search(seg) for seg in segments[:3])


def detect_placeholder(text: str, url: str = "") -> str | None:
    """内容级判定：返回 `"placeholder"` / `"ad"` / None。"""
    if url and _AD_SEGMENT_RE.search(url):
        return "ad"
    if playlist_is_placeholder(text):
        return "placeholder"
    if playlist_is_ad(text):
        return "ad"
    return None
