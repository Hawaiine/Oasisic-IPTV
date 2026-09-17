"""探活分列生成单测（不联网）。"""

from __future__ import annotations

import probe
from lib.health import HTTP_403, OK


def _entry(name: str, url: str, group: str = "卫视") -> dict:
    return {"name": name, "url": url, "group": group, "tvg_id": "X", "tvg_logo": ""}


def test_write_columns_caps_per_name(tmp_path):
    entries = [_entry("湖南卫视", f"http://cm/{i}.m3u8") for i in range(5)]
    results = {e["url"]: {"level": HTTP_403} for e in entries}
    counts = probe.write_columns(entries, results, {}, url_tvg="tvg", out_dir=tmp_path)
    assert counts["cmcc"] == 3  # 同频道最多 3 条
    text = (tmp_path / "live_cmcc.m3u").read_text(encoding="utf-8")
    assert text.count("#EXTINF") == 3
    assert text.startswith('#EXTM3U url-tvg="tvg"')


def test_write_columns_classifies_and_skips_ok_ipv6(tmp_path):
    v6_ok = "http://[2409:8087:8:21::18]:6610/ok/1.m3u8"
    v6_dead = "http://[2409:8087:8:21::18]:6610/dead/1.m3u8"
    signed = "http://cdn.example/live.m3u8?auth_key=abc"
    plain = "http://cdn.example/plain.m3u8"
    entries = [
        _entry("央视", v6_ok),
        _entry("北京卫视", v6_dead),
        _entry("东方卫视", signed),
        _entry("江苏卫视", plain),
    ]
    results = {
        v6_ok: {"level": OK},
        v6_dead: {"level": "ipv6-no-route"},
        signed: {"level": OK},
        plain: {"level": OK},
    }
    counts = probe.write_columns(entries, results, {}, url_tvg="tvg", out_dir=tmp_path)
    assert counts == {"ipv6": 1, "cmcc": 0, "signed": 1}
    ipv6_text = (tmp_path / "live_ipv6.m3u").read_text(encoding="utf-8")
    assert v6_dead in ipv6_text
    assert v6_ok not in ipv6_text  # 可播的 v6 链接不进「仅 IPv6」清单
    signed_text = (tmp_path / "live_signed.m3u").read_text(encoding="utf-8")
    assert signed in signed_text


def test_write_columns_empty_lists_are_headers_only(tmp_path):
    counts = probe.write_columns([], {}, {}, url_tvg="tvg", out_dir=tmp_path)
    assert counts == {"ipv6": 0, "cmcc": 0, "signed": 0}
    for name in ("live_ipv6.m3u", "live_cmcc.m3u", "live_signed.m3u"):
        text = (tmp_path / name).read_text(encoding="utf-8")
        assert text.startswith('#EXTM3U url-tvg="tvg"')
        assert "#EXTINF" not in text