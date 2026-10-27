from pathlib import Path

from lib.m3u import build_m3u, clean_leaked_name, parse_m3u, parse_playlist, parse_txt, split_extinf


FIXTURE = Path(__file__).parent / "fixtures" / "sample.m3u"


def test_parse_sample_m3u() -> None:
    text = FIXTURE.read_text(encoding="utf-8")
    entries = parse_m3u(text)
    assert len(entries) == 5
    assert entries[0]["name"] == "CCTV1HD综合"
    assert entries[0]["url"].startswith("http")


def test_parse_txt_genre() -> None:
    text = "央视,#genre#\nCCTV1,http://x/1\n卫视,#genre#\n湖南卫视,http://x/2\n"
    entries = parse_txt(text)
    assert len(entries) == 2
    assert entries[0]["group"] == "央视"


def test_build_roundtrip() -> None:
    src = [
        {
            "display_name": "CCTV-1 综合",
            "url": "http://x/1",
            "group_title": "央视",
            "tvg_id": "CCTV1",
        }
    ]
    text = build_m3u(src, playlist_title="t")
    assert text.startswith('#EXTM3U url-tvg="https://live.fanmingming.com/e.xml"')
    back = parse_playlist(text, "m3u")
    assert back[0]["name"] == "CCTV-1 综合"
    assert back[0]["group"] == "央视"


def test_split_extinf_ignores_comma_inside_quotes() -> None:
    payload = '-1 tvg-id="X" http-user-agent="Mozilla/5.0 (Windows NT 10.0; Win64, x86)" group-title="Movies",真实频道,带逗号'
    _head, name = split_extinf(payload)
    assert name == "真实频道,带逗号"


def test_parse_m3u_keeps_name_when_attr_has_comma() -> None:
    text = (
        '#EXTM3U\n'
        '#EXTINF:-1 tvg-id="Y" http-user-agent="Mozilla/5.0 (Windows NT 10.0) Chrome/149",FILMBOX+ Love & Crime\n'
        "http://x/1\n"
    )
    entries = parse_m3u(text)
    assert len(entries) == 1
    assert entries[0]["name"] == "FILMBOX+ Love & Crime"
    assert entries[0]["tvg_id"] == "Y"


def test_parse_m3u_repairs_duplicated_attr_block() -> None:
    """上游把属性块写了两遍时，名称不能吞下属性原文。"""
    text = (
        '#EXTM3U\n'
        '#EXTINF:-1 group-title="卫视",tvg-id="云南卫视" tvg-name="云南卫视" '
        'tvg-logo="https://example.com/y.png" group-title="卫视 ",云南卫视\n'
        "http://x/2\n"
    )
    entries = parse_m3u(text)
    assert entries[0]["name"] == "云南卫视"


def test_clean_leaked_name_noop_for_normal_names() -> None:
    assert clean_leaked_name("CCTV-1 综合") == "CCTV-1 综合"
    assert clean_leaked_name("") == ""
