"""选优接入 URL 健康度：有数据时健康度优先，无数据时行为与旧版一致。"""

from __future__ import annotations

from lib.health import HTTP_403, HTTP_404, OK, UNKNOWN
from lib.select import select_best


def _entry(url: str, *, name: str = "CCTV-1 综合", prio: int, site: str = "src", region: str = "cn") -> dict:
    return {
        "name": name,
        "url": url,
        "standard_name": name,
        "display_name": name,
        "category": "cctv",
        "matched": True,
        "source_key": site,
        "source_region": region,
        "source_priority": prio,
    }


def test_without_health_keeps_legacy_order():
    """health=None：仍是源 priority 说话（旧行为）。"""
    entries = [
        _entry("http://cmcc.example/1.m3u8", prio=10),
        _entry("http://public.example/1.m3u8", prio=90),
    ]
    picked = select_best(entries, max_keep=1)
    assert [e["url"] for e in picked] == ["http://cmcc.example/1.m3u8"]


def test_health_beats_source_priority():
    """低优先级但实测可播的 URL 胜过高优先级但 403 网络锁的 URL。"""
    entries = [
        _entry("http://cmcc.example/1.m3u8", prio=10),
        _entry("http://public.example/1.m3u8", prio=90),
    ]
    health = {"http://cmcc.example/1.m3u8": HTTP_403, "http://public.example/1.m3u8": OK}
    picked = select_best(entries, max_keep=1, health=health)
    assert [e["url"] for e in picked] == ["http://public.example/1.m3u8"]


def test_health_dead_link_loses_to_unknown():
    """已判定死链的 URL 让位给「未探测」的 URL。"""
    entries = [
        _entry("http://dead.example/1.m3u8", prio=1),
        _entry("http://new.example/1.m3u8", prio=99),
    ]
    health = {"http://dead.example/1.m3u8": HTTP_404}
    picked = select_best(entries, max_keep=1, health=health)
    assert [e["url"] for e in picked] == ["http://new.example/1.m3u8"]


def test_all_unknown_health_falls_back_to_priority():
    """健康数据覆盖不到时（全是 unknown），排序与旧版一致。"""
    entries = [
        _entry("http://a.example/1.m3u8", prio=10),
        _entry("http://b.example/1.m3u8", prio=90),
    ]
    health = {"http://other.example/1.m3u8": OK}
    picked = select_best(entries, max_keep=1, health=health)
    assert [e["url"] for e in picked] == ["http://a.example/1.m3u8"]


def test_dedup_same_url_keeps_better_metadata():
    """同一 URL 出现在多个源时，去重保留排序更优的那条记录（URL 相同 → 健康度相同）。"""
    url = "http://dup.example/1.m3u8"
    entries = [
        _entry(url, name="A台", prio=10, site="fast-src"),
        _entry(url, name="A台", prio=80, site="slow-src"),
    ]
    picked = select_best(entries, max_keep=1, health={url: OK})
    assert len(picked) == 1
    assert picked[0]["source_key"] == "fast-src"


def test_backup_keep_three_with_health():
    """备份列表 max_keep=3 时按健康度排序取前三。"""
    entries = [
        _entry("http://u1/1.m3u8", prio=10),
        _entry("http://u2/1.m3u8", prio=20),
        _entry("http://u3/1.m3u8", prio=30),
        _entry("http://u4/1.m3u8", prio=40),
    ]
    health = {
        "http://u1/1.m3u8": HTTP_403,
        "http://u2/1.m3u8": UNKNOWN,
        "http://u3/1.m3u8": OK,
        "http://u4/1.m3u8": OK,
    }
    picked = select_best(entries, max_keep=3, health=health)
    urls = [e["url"] for e in picked]
    assert urls[:2] == ["http://u3/1.m3u8", "http://u4/1.m3u8"]
    assert urls[2] == "http://u2/1.m3u8"