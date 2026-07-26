# coding: utf-8
"""
Classification fallback for channel names that don't match the standard table.

Priority
--------
1. Standard table match (handled by caller) → use its category + group_title
2. Source region hint (handled by caller) → hotel→special, overseas→overseas
3. Keyword / regex rules below → assign category + group_title
4. Chinese name with no strong feature → local (prefer domestic)
5. Pure Latin / no Chinese → overseas
"""

from __future__ import annotations

import re
import typing as t

from lib import categories as cat

# ── Rule definitions ───────────────────────────────────────────────
# Each rule: (category_key, patterns)
# patterns are matched against the lowercased channel name.

_RULES: list[tuple[str, list[str]]] = [
    ("cctv", [
        r"\bcctv\b", r"\bcetv\b", r"央视", r"中央\d", r"中国教育",
        r"cctv体育", r"cctv新闻", r"cctv\d",
    ]),
    ("weishi", [
        r"卫视", r"卫星", r"东南台",
    ]),
    ("gangtai", [
        r"香港", r"台湾", r"澳门", r"\btvb\b", r"凤凰", r"phoenix",
        r"无线", r"翡翠", r"星空", r"华娱", r"卫视中文",
        r"中天", r"东森", r"八大", r"纬来", r"民视", r"三立",
        r"寰宇", r"星卫", r"龙祥", r"好莱坞", r"明珠台",
    ]),
    ("sports", [
        r"体育", r"\bespn\b", r"足球", r"篮球", r"\bnba\b", r"英超",
        r"中超", r"\bcba\b", r"乒", r"羽", r"台球", r"搏击",
        r"咪咕", r"竞技", r"赛事", r"cctv5",
    ]),
    ("live", [
        r"斗鱼", r"虎牙", r"\bbilibili\b", r"b站", r"哔哩",
        r"直播", r"\bdouyu\b", r"\bhuya\b",
    ]),
    ("radio", [
        r"电台", r"广播", r"fm\s*\d", r"am\s*\d",
        r"\bradio\b", r"央广", r"音乐之声",
    ]),
    ("overseas", [
        r"\bbbc\b", r"\bcnn\b", r"\bfox\b", r"\bnbc\b", r"\babc\b", r"\bcbs\b",
        r"\bdiscovery\b", r"nat\.geo", r"national geographic",
        r"\bhbo\b", r"\bmtv\b", r"\beuro\b", r"france\d", r"\baljazeera\b",
        r"\bdw\b[\s-]", r"\brt\b[\s-]", r"\bnhk\b", r"\bfuji\b",
        r"\btbs\b", r"tv asahi", r"tv tokyo",
    ]),
    ("local", [
        r"^(北京|上海|天津|重庆|广东|广州|深圳|浙江|杭州|江苏|南京"
        r"|山东|济南|青岛|四川|成都|湖北|武汉|湖南|长沙"
        r"|福建|福州|厦门|河南|郑州|河北|石家庄|辽宁|沈阳"
        r"|吉林|长春|黑龙江|哈尔滨|山西|太原|陕西|西安"
        r"|甘肃|兰州|青海|西宁|云南|昆明|贵州|贵阳"
        r"|海南|海口|广西|南宁|内蒙古|新疆|西藏|宁夏"
        r"|江西|南昌|安徽|合肥|大连|宁波|苏州"
        r"|无锡|佛山|东莞|珠海|中山|惠州|汕头|湛江"
        r"|温州|绍兴|嘉兴|泉州|漳州|柳州|桂林|三亚"
        r"|澳门|香港|台湾)",
        r"^(北京|上海|天津|重庆|广东|广州|深圳|浙江|杭州|江苏|南京"
        r"|山东|济南|青岛|四川|成都|湖北|武汉|湖南|长沙"
        r"|福建|福州|厦门|河南|郑州|河北|石家庄|辽宁|沈阳"
        r"|吉林|长春|黑龙江|哈尔滨|山西|太原|陕西|西安"
        r"|甘肃|兰州|青海|西宁|云南|昆明|贵州|贵阳"
        r"|海南|海口|广西|南宁|内蒙古|新疆|西藏|宁夏"
        r"|江西|南昌|安徽|合肥|大连|宁波|苏州"
        r"|无锡|佛山|东莞|珠海|中山|惠州|汕头|湛江"
        r"|温州|绍兴|嘉兴|泉州|漳州|柳州|桂林|三亚"
        r"|澳门|香港|台湾).{1,4}(台|频道|影视|综合|公共|新闻|卫视|都市)",
    ]),
]


def _has_chinese(text: str) -> bool:
    return bool(re.search(r"[\u4e00-\u9fff]", text))


def classify_by_rules(
    name: str,
    group_title_from_source: str = "",
) -> tuple[str, str]:
    """
    Classify a channel name using keyword rules.

    Parameters
    ----------
    name : str
        Cleaned channel name.
    group_title_from_source : str
        Group title from the source M3U (fallback hint).

    Returns
    -------
    tuple[str, str]
        (category_key, group_title) — group_title is the canonical one
        from ``categories.group_title()``.
    """
    name_lower = name.lower().strip()
    if not name_lower:
        return "other", cat.group_title("other")

    for key, patterns in _RULES:
        for pat in patterns:
            if re.search(pat, name_lower):
                return key, cat.group_title(key)

    # Source group_title hint
    g = group_title_from_source.lower().strip()
    if "央视" in g or "cctv" in g:
        return "cctv", cat.group_title("cctv")
    if "卫视" in g:
        return "weishi", cat.group_title("weishi")
    if "体育" in g:
        return "sports", cat.group_title("sports")
    if "电台" in g or "radio" in g:
        return "radio", cat.group_title("radio")
    if "酒店" in g or "special" in g:
        return "special", cat.group_title("special")

    # Chinese name with no strong feature → local
    if _has_chinese(name):
        return "local", cat.group_title("local")

    # Pure Latin → overseas
    return "overseas", cat.group_title("overseas")