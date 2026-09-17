"""EPG 多源合并单测（不联网）。"""

from __future__ import annotations

import xml.etree.ElementTree as ET

from fetch_epg import merge_and_clip, xml_bytes


def _blob(channels: list[tuple[str, str]], progs: list[tuple[str, str, str]]) -> str:
    parts = ["<tv>"]
    for cid, name in channels:
        parts.append(f'<channel id="{cid}"><display-name>{name}</display-name></channel>')
    for cid, start, stop in progs:
        parts.append(f'<programme start="{start}" stop="{stop}" channel="{cid}"><title>t</title></programme>')
    parts.append("</tv>")
    return "".join(parts)


def test_merge_two_sources_and_clip():
    a = _blob([("CCTV1", "CCTV1")], [("CCTV1", "20260918060000 +0800", "20260918070000 +0800")])
    b = _blob(
        [("湖南卫视", "湖南卫视"), ("湖南卫视-dup", "湖南卫视")],
        [
            ("湖南卫视", "20260918080000 +0800", "20260918090000 +0800"),
            ("湖南卫视-dup", "20260918100000 +0800", "20260918110000 +0800"),
        ],
    )
    allowed = {"CCTV1", "湖南卫视"}
    root, stats, per_source = merge_and_clip([("src-a", a), ("src-b", b)], allowed)
    ids = [ch.get("id") for ch in root.findall("channel")]
    assert ids == ["CCTV1", "湖南卫视"]  # 未在 allowed 的 -dup 被裁掉
    assert stats["channel_kept"] == 2
    assert stats["channel_skipped"] == 1
    assert stats["programme_kept"] == 2
    assert per_source["src-a"]["programme_kept"] == 1
    assert per_source["src-b"]["programme_kept"] == 1


def test_duplicate_programme_deduped_across_sources():
    prog = ("CCTV2", "20260918060000 +0800", "20260918070000 +0800")
    a = _blob([("CCTV2", "CCTV2")], [prog])
    b = _blob([("CCTV2", "CCTV2")], [prog])
    root, stats, per_source = merge_and_clip([("a", a), ("b", b)], {"CCTV2"})
    assert stats["programme_kept"] == 1
    assert stats["programme_dup"] == 1
    assert per_source["b"]["programme_kept"] == 0


def test_parse_fail_does_not_abort_others():
    good = _blob([("CCTV3", "CCTV3")], [("CCTV3", "20260918060000 +0800", "20260918070000 +0800")])
    root, stats, per_source = merge_and_clip([("bad", "<tv><channel"), ("good", good)], {"CCTV3"})
    assert stats["parse_fail"] == 1
    assert stats["channel_kept"] == 1
    assert per_source["bad"]["parse_fail"] == 1


def test_xml_bytes_has_declaration():
    root = ET.Element("tv")
    data = xml_bytes(root)
    assert data.startswith(b'<?xml version="1.0" encoding="UTF-8"?>')