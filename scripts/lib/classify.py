# coding: utf-8
"""
Classification fallback for channel names that don't match the standard table.

Priority
--------
1. Standard table match (handled by caller) → use its category + group_title
2. Keyword / regex rules below → assign category + group_title
3. Fallback → other
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
        r"cctv", r"cetv", r"央视", r"中央\d", r"中国教育",
        r"cctv体育", r"cctv新闻",
    ]),
    ("weishi", [
        r"卫视", r"卫星", r"东南台",
    ]),
    ("gangtai", [
        r"香港", r"台湾", r"澳门", r"tvb", r"凤凰", r"phoenix",
        r"无线", r"翡翠", r"星空", r"华娱", r"卫视中文",
        r"中天", r"东森", r"八大", r"纬来", r"民视", r"三立",
        r"寰宇", r"星卫", r"龙祥", r"好莱坞",
    ]),
    ("sports", [
        r"体育", r"espn", r"足球", r"篮球", r"nba", r"英超",
        r"中超", r"cba", r"乒", r"羽", r"台球", r"搏击",
        r"咪咕", r"竞技", r"赛事",
    ]),
    ("live", [
        r"斗鱼", r"虎牙", r"bilibili", r"b站", r"哔哩",
        r"直播", r"douyu", r"huya",
    ]),
    ("overseas", [
        r"^[a-z]{2,}$",           # Short English-only names
        r"bbc", r"cnn", r"fox", r"nbc", r"abc", r"cbs",
        r"discovery", r"nat.geo", r"national geographic",
        r"hbo", r"mtv", r"euro", r"france\d", r"aljazeera",
        r"dw[\s-]", r"rt[\s-]", r"nhk", r"fuji",
        r"tbs", r"tv asahi", r"tv tokyo", r"ani",
    ]),
    ("radio", [
        r"电台", r"广播", r"fm\s*\d", r"am\s*\d",
        r"radio", r"央广",
    ]),
    ("local", [
        # Matches Chinese province/city names (2 chars) followed by common TV suffixes
        r"^(北京|上海|天津|重庆|广东|广州|深圳|浙江|杭州|江苏|南京"
        r"|山东|济南|青岛|四川|成都|湖北|武汉|湖南|长沙"
        r"|福建|福州|厦门|河南|郑州|河北|石家庄|辽宁|沈阳"
        r"|吉林|长春|黑龙江|哈尔滨|山西|太原|陕西|西安"
        r"|甘肃|兰州|青海|西宁|云南|昆明|贵州|贵阳"
        r"|海南|海口|广西|南宁|内蒙古|新疆|西藏|宁夏"
        r"|江西|南昌|安徽|合肥|大连|宁波|厦门|苏州"
        r"|无锡|佛山|东莞|珠海|中山|惠州|汕头|湛江"
        r"|温州|绍兴|嘉兴|泉州|漳州|柳州|桂林|三亚"
        r"|澳门|香港|台湾)",
        r"^(北京|上海|天津|重庆|广东|广州|深圳|浙江|杭州|江苏|南京"
        r"|山东|济南|青岛|四川|成都|湖北|武汉|湖南|长沙"
        r"|福建|福州|厦门|河南|郑州|河北|石家庄|辽宁|沈阳"
        r"|吉林|长春|黑龙江|哈尔滨|山西|太原|陕西|西安"
        r"|甘肃|兰州|青海|西宁|云南|昆明|贵州|贵阳"
        r"|海南|海口|广西|南宁|内蒙古|新疆|西藏|宁夏"
        r"|江西|南昌|安徽|合肥|大连|宁波|厦门|苏州"
        r"|无锡|佛山|东莞|珠海|中山|惠州|汕头|湛江"
        r"|温州|绍兴|嘉兴|泉州|漳州|柳州|桂林|三亚"
        r"|澳门|香港|台湾).{1,4}(台|频道|影视|综合|公共|新闻|卫视|都市)",
    ]),
]


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

    # If source group_title contains Chinese TV keywords, use it
    g = group_title_from_source.lower().strip()
    if "央视" in g or "cctv" in g:
        return "cctv", cat.group_title("cctv")
    if "卫视" in g:
        return "weishi", cat.group_title("weishi")
    if "体育" in g:
        return "sports", cat.group_title("sports")
    if "电台" in g or "radio" in g:
        return "radio", cat.group_title("radio")

    return "other", cat.group_title("other")