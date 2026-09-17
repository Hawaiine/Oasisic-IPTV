"""health 分级与健康索引单测。"""

from __future__ import annotations

from datetime import datetime, timedelta

from lib.health import (
    CST,
    HTTP_403,
    HTTP_404,
    IPV6_NO_ROUTE,
    OK,
    PLAYLIST_MISSING,
    RTP,
    TIMEOUT,
    UNKNOWN,
    build_index,
    grade,
    index_age_days,
    is_cmcc_host,
    is_ipv6_literal,
    is_signed,
    level_rank,
    looks_like_playlist,
    summarize,
)

V6_URL = "http://[2409:8087:8:21::18]:6610/otttv.bj.chinamobile.com/PLTV/88888888/1.m3u8?"


def test_is_signed_only_query_params():
    assert is_signed("http://example.com/live.m3u8?token=1") is True
    assert is_signed("http://example.com/live.m3u8?auth_key=abc") is True
    assert is_signed("http://example.com/live.m3u8?hdnts=st=1~exp=2") is True
    assert is_signed("http://example.com/path/sign.m3u8") is False
    assert is_signed("http://token.example/live.m3u8") is False
    assert is_signed("") is False


def test_ipv6_literal_detection():
    assert is_ipv6_literal(V6_URL) is True
    assert is_ipv6_literal("http://gslbserv.itv.cmvideo.cn/1.m3u8") is False


def test_cmcc_host_detection():
    assert is_cmcc_host("http://gslbserv.itv.cmvideo.cn/1.m3u8") is True
    assert is_cmcc_host("http://ottrrs.hl.chinamobile.com/x.m3u8") is True
    assert is_cmcc_host("https://stream1.freetv.fun/x.m3u8") is False


def test_looks_like_playlist():
    assert looks_like_playlist(b"#EXTM3U\n#EXTINF:-1,x") is True
    assert looks_like_playlist(b"\x47\x40\x11") is True
    assert looks_like_playlist(b"<html><body>403</body></html>") is False
    assert looks_like_playlist(b"") is False


def test_grade_http_paths():
    assert grade(url="http://a/x.m3u8", status=200, body_head=b"#EXTM3U\n#EXTINF:-1,x") == OK
    assert grade(url="http://a/x.m3u8", status=206, body_head=b"\x47\x00") == OK
    assert grade(url="http://a/x.m3u8", status=200, body_head=b"<html>nope</html>") == PLAYLIST_MISSING
    assert grade(url="http://a/x.m3u8", status=403) == HTTP_403
    assert grade(url="http://a/x.m3u8", status=404) == HTTP_404
    assert grade(url="http://a/x.m3u8", status=502) == "http-error"


def test_grade_error_paths():
    assert grade(url="http://a/x.m3u8", error_type="ClientConnectorError", error_msg="Timeout on reading") == TIMEOUT
    assert grade(url="http://a/x.m3u8", error_type="ClientConnectorDNSError", error_msg="Name or service not known") == "dns-fail"
    assert grade(url=V6_URL, error_type="OSError", error_msg="[Errno 101] Network is unreachable") == IPV6_NO_ROUTE
    assert grade(url="http://a/x", error_type="OSError", error_msg="[Errno 101] Network is unreachable") == "conn-fail"
    assert grade(url="rtp://239.1.1.1:5000") == RTP


def test_grade_aiohttp_ssl_default_not_misread():
    """aiohttp 的连接错误消息里带 `ssl:default`，不得被误判成 ssl-fail。"""
    v6_msg = "Cannot connect to host 2409:8087:8:21::18:6610 ssl:default [Network is unreachable]"
    assert grade(url=V6_URL, error_type="ClientConnectorError", error_msg=v6_msg) == IPV6_NO_ROUTE
    dns_msg = "Cannot connect to host v.hystudio.cn:8088 ssl:default [Name or service not known]"
    assert grade(url="https://v.hystudio.cn:8088/live/x.m3u8", error_type="ClientConnectorDNSError", error_msg=dns_msg) == "dns-fail"
    # 真正的证书错误仍判 ssl-fail
    assert grade(url="https://a/x.m3u8", error_type="ClientConnectorSSLError", error_msg="ssl:default") == "ssl-fail"
    assert grade(url="https://a/x.m3u8", error_type="ClientConnectorError", error_msg="certificate verify failed ssl:default") == "ssl-fail"


def test_level_rank_ordering():
    assert level_rank(OK) < level_rank(PLAYLIST_MISSING) < level_rank(UNKNOWN)
    assert level_rank(UNKNOWN) < level_rank(HTTP_403) < level_rank(HTTP_404)
    assert level_rank("不存在的分级") == level_rank(UNKNOWN)


def test_build_index_fresh_and_stale():
    now = datetime(2026, 9, 18, 12, 0, 0, tzinfo=CST)
    fresh = (now - timedelta(days=1)).strftime("%Y-%m-%d %H:%M:%S")
    stale = (now - timedelta(days=30)).strftime("%Y-%m-%d %H:%M:%S")
    payload = {
        "schema_version": 1,
        "generated_at": fresh,
        "urls": {
            "http://a/1.m3u8": {"level": OK, "checked_at": fresh},
            "http://a/2.m3u8": {"level": OK, "checked_at": stale},
            "http://a/3.m3u8": {"level": HTTP_403, "checked_at": fresh},
        },
    }
    index = build_index(payload, max_age_days=7, now=now)
    assert index["http://a/1.m3u8"] == OK
    assert index["http://a/2.m3u8"] == UNKNOWN  # 过期 → 不奖惩
    assert index["http://a/3.m3u8"] == HTTP_403
    assert build_index(None) == {}
    assert build_index({"urls": []}) == {}


def test_index_age_days_and_summarize():
    now = datetime(2026, 9, 18, 12, 0, 0, tzinfo=CST)
    payload = {
        "generated_at": "2026-09-16 12:00:00",
        "urls": {"http://a/1.m3u8": {"level": OK, "checked_at": "2026-09-16 12:00:00"}},
    }
    assert index_age_days(payload, now=now) == 2.0
    assert index_age_days({}) is None
    text = summarize({"u1": OK, "u2": OK, "u3": HTTP_403})
    assert text.startswith("ok=2")
    assert summarize({}) == "-"