"""黑名单与分类回退单测。"""

from __future__ import annotations

from lib.classify import classify_name
from lib.exclude import DEFAULT_PATTERNS, is_excluded, load_patterns


def test_default_blacklist_hits_junk():
    for name in ("2019年春晚", "2021春晚", "JJ斗地主", "乐家购物", "测试频道", "加群看片", "彩票直播", "12345", "   "):
        assert is_excluded(name, list(DEFAULT_PATTERNS)), name


def test_default_blacklist_keeps_real_channels():
    for name in (
        "河南民生",
        "山东生活",
        "CCTV-5+ 体育赛事",
        "凤凰卫视香港台",
        "澳视澳门",
        "武汉新闻综合",
        "CHC家庭影院",
        "快乐垂钓",
        "金色学堂",
    ):
        assert not is_excluded(name, list(DEFAULT_PATTERNS)), name


def test_load_patterns_from_config():
    cfg = {"patterns": ["foo", "", "bar"]}
    assert load_patterns(cfg) == ["foo", "bar"]
    assert load_patterns(None) == list(DEFAULT_PATTERNS)
    assert load_patterns({}) == list(DEFAULT_PATTERNS)


def test_classify_local_long_tail():
    assert classify_name("河南民生", "cn") == "local"
    assert classify_name("山东生活", "cn") == "local"
    assert classify_name("黑龙江影视", "cn") == "local"
    assert classify_name("BRTV卡酷少儿", "cn") == "local"
    assert classify_name("快乐垂钓", "cn") == "sports"
    assert classify_name("风云足球", "cn") == "sports"
    assert classify_name("凤凰中文", "hk_tw") == "gangtai"
    assert classify_name("纬来体育", "hk_tw") == "gangtai"
    assert classify_name("CCTV第一剧场", "cn") == "cctv"
    assert classify_name("CGTN阿语", "cn") == "cctv"
    assert classify_name("某不认识的名字", "cn") == "other"


def test_classify_overseas_region_wins():
    assert classify_name("某不认识的名字", "overseas") == "overseas"
    assert classify_name("某不认识的名字", "hotel") == "hotel"