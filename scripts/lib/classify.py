"""未命中标准表时的关键词分类回退。命中标准表的条目沿用表内 category。"""

from __future__ import annotations

import re
from typing import Any

from .categories import group_title, is_known

_RULES: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"CCTV|央视|CGTN|CETV|中国教育", re.I), "cctv"),
    # 凤凰卫视等必须先于「卫视」，否则会被误分为大陆卫视
    (re.compile(r"凤凰|TVB|翡翠|明珠|无线|HOY|ViuTV|Now\s*TV|中天|东森|华视|台视|中视|民视|TVBS|三立|澳门|澳视|RTHK|港台", re.I), "gangtai"),
    (re.compile(r"卫视"), "weishi"),
    (re.compile(r"体育|赛事|足球|篮球|NBA|英超|西甲|意甲|德甲|奥运"), "sports"),
    (re.compile(r"斗鱼|虎牙|B站|哔哩|直播间|熊猫"), "live"),
    (re.compile(r"电台|广播|FM\d|AM\d|Radio", re.I), "radio"),
    (re.compile(r"酒店|Hotel", re.I), "hotel"),
]


def classify_name(name: str, source_region: str = "") -> str:
    text = name or ""
    for pat, cat in _RULES:
        if pat.search(text):
            return cat
    if source_region == "hotel":
        return "hotel"
    if source_region == "overseas":
        return "overseas"
    if source_region in {"cn", "hk_tw"}:
        # 国内未匹配台优先归地方，避免全部泄洪到 other
        if re.search(r"(新闻|综合|都市|影视|公共|少儿|文艺|生活|经济)", text):
            return "local"
    return "other"


def classify_entries(entries: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for e in entries:
        rec = dict(e)
        cat = rec.get("category") or ""
        if rec.get("matched") and is_known(cat):
            rec["group_title"] = group_title(cat)
            out.append(rec)
            continue
        cat = classify_name(
            rec.get("cleaned_name") or rec.get("name") or "",
            rec.get("source_region") or "",
        )
        rec["category"] = cat
        rec["group_title"] = group_title(cat)
        out.append(rec)
    return out
