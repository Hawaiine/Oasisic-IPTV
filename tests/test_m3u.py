from pathlib import Path

from lib.m3u import build_m3u, parse_m3u, parse_playlist, parse_txt


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
