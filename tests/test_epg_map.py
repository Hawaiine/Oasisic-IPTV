"""EPG 对齐规则单测（不联网）。"""

from __future__ import annotations

from lib.epg_map import (
    build_missing_report,
    choose_epg_id,
    load_epg_ids,
    parse_channels_with_names,
)

CH = {
    "standard_name": "湖南卫视",
    "display_name": "湖南卫视",
    "category": "weishi",
    "tvg_id": "HunanTV",
}


def test_match_by_tvg_id_direct():
    epg_id, reason = choose_epg_id(
        {**CH, "tvg_id": "CCTV1", "display_name": "CCTV-1 综合"},
        ids_all={"CCTV1"},
        ids_with_programme={"CCTV1"},
    )
    assert (epg_id, reason) == ("CCTV1", "matched:tvg_id")


def test_match_by_display_name_direct():
    epg_id, reason = choose_epg_id(CH, ids_all={"湖南卫视"}, ids_with_programme={"湖南卫视"})
    assert (epg_id, reason) == ("湖南卫视", "matched:display_name")


def test_match_by_name_index_for_numeric_upstream():
    epg_id, reason = choose_epg_id(
        CH,
        ids_all={"539871"},
        ids_with_programme={"539871"},
        name_index={"湖南卫视": "539871"},
    )
    assert epg_id == "539871"
    assert reason.startswith("matched-name:")


def test_match_via_alias():
    epg_id, reason = choose_epg_id(
        {**CH, "standard_name": "浙江钱江"},
        ids_all={"钱江"},
        ids_with_programme={"钱江"},
        aliases={"浙江钱江": ["钱江都市", "钱江"]},
    )
    assert (epg_id, reason) == ("钱江", "matched:alias")


def test_upstream_channel_without_programme_is_not_used():
    epg_id, reason = choose_epg_id(
        {**CH, "standard_name": "澳视澳门"},
        ids_all={"澳视澳门"},
        ids_with_programme=set(),
    )
    assert epg_id is None
    assert reason == "upstream-no-programme:澳视澳门"


def test_upstream_missing():
    epg_id, reason = choose_epg_id({**CH, "standard_name": "武汉新闻"}, ids_all=set(), ids_with_programme=set())
    assert epg_id is None
    assert reason == "upstream-missing"


def test_build_missing_report_lines():
    channels = [
        {**CH},
        {"standard_name": "武汉新闻", "display_name": "武汉新闻", "category": "local", "tvg_id": "WHXW"},
    ]
    mapping, missing = build_missing_report(
        channels,
        ids_all={"湖南卫视"},
        ids_with_programme={"湖南卫视"},
    )
    assert mapping["湖南卫视"]["epg_id"] == "湖南卫视"
    assert mapping["武汉新闻"]["epg_id"] is None
    assert missing == ["武汉新闻 | local | upstream-missing"]


def test_load_epg_ids_includes_both_fields():
    channels = [
        {"standard_name": "A", "tvg_id": "A1", "epg_id": "湖南卫视"},
        {"standard_name": "B", "tvg_id": "B1"},
        {"standard_name": "C", "tvg_id": "C1", "epg_id": None},
    ]
    assert load_epg_ids(channels) == {"湖南卫视", "A1", "B1", "C1"}


def test_parse_channels_with_names():
    xml = (
        '<tv><channel id="539871"><display-name lang="CN">翡翠台</display-name>'
        "<icon src=\"\" /></channel>"
        '<channel id="CCTV1"><display-name>CCTV1</display-name></channel></tv>'
    )
    assert parse_channels_with_names(xml) == {"539871": ["翡翠台"], "CCTV1": ["CCTV1"]}