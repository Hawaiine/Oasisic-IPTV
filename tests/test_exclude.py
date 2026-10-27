"""黑名单与分类回退单测。"""

from __future__ import annotations

from pathlib import Path

import yaml

from lib.classify import classify_name
from lib.exclude import DEFAULT_PATTERNS, filter_entries, is_excluded, load_patterns

CONFIG = Path(__file__).resolve().parent.parent / "config" / "exclude.yaml"


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

def _config_patterns() -> list[str]:
    return load_patterns(yaml.safe_load(CONFIG.read_text(encoding="utf-8")))


def test_config_keeps_real_short_names():
    """回归：短代号规则曾把 CGTN/CCTV5/BTV 等真频道当垃圾丢掉。"""
    pats = _config_patterns()
    for name in ("CGTN", "CCTV5", "CCTV8", "CCTV12", "BTV", "BRTV", "CETV", "SMG", "DW", "ViuTV"):
        assert not is_excluded(name, pats), name


def test_config_still_drops_junk_codes():
    pats = _config_patterns()
    for name in ("CH5", "M2", "NU", "HKS"):
        assert is_excluded(name, pats), name


def test_filter_entries_checks_cleaned_name():
    """回归：`4K超清` 清洗后是 `4K`，只在原名上匹配会漏网。"""
    pats = _config_patterns()
    kept, dropped = filter_entries([{"name": "4K超清"}, {"name": "湖南卫视"}], pats)
    assert dropped == ["4K超清"]
    assert [e["name"] for e in kept] == ["湖南卫视"]


def test_config_drops_placeholder_names():
    pats = _config_patterns()
    for name in ("CCTV-1 无信号", "测试卡", "彩条信号", "敬请期待"):
        assert is_excluded(name, pats), name
    for name in ("CCTV-1 综合", "湖南卫视"):
        assert not is_excluded(name, pats), name
