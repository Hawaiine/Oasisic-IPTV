"""URL 健康度：探活结果分级、排序权重、健康索引加载（纯函数，无 IO 副作用）。"""

from __future__ import annotations

import re
from datetime import datetime, timedelta, timezone
from typing import Any

CST = timezone(timedelta(hours=8))

# ── 分级常量 ───────────────────────────────────────────────
OK = "ok"
PLAYLIST_MISSING = "playlist-missing"
TIMEOUT = "timeout"
HTTP_ERROR = "http-error"
SSL_FAIL = "ssl-fail"
CONN_FAIL = "conn-fail"
DNS_FAIL = "dns-fail"
IPV6_NO_ROUTE = "ipv6-no-route"
HTTP_403 = "http-403"
HTTP_404 = "http-404"
RTP = "rtp"
UNKNOWN = "unknown"

# 越可靠 rank 越小。unknown/not-probed 落在中间：既不奖励也不惩罚，
# 这样「没有任何健康数据」时排序与旧版完全一致。
LEVEL_RANK: dict[str, int] = {
    OK: 0,
    PLAYLIST_MISSING: 1,
    TIMEOUT: 2,
    HTTP_ERROR: 2,
    SSL_FAIL: 3,
    UNKNOWN: 3,
    RTP: 3,
    HTTP_403: 4,
    IPV6_NO_ROUTE: 4,
    CONN_FAIL: 4,
    DNS_FAIL: 5,
    HTTP_404: 5,
}
UNKNOWN_RANK = LEVEL_RANK[UNKNOWN]

# 连续失败即视为死链（不应占据主列表）
DEAD_LEVELS = {HTTP_404, DNS_FAIL}
# 网络锁 / 仅 IPv6：链路类型问题，不是内容失效
LOCKED_LEVELS = {HTTP_403, IPV6_NO_ROUTE}
# 不参与探活的协议（组播）
UNPROBEABLE_SCHEMES = ("rtp://", "udp://", "rtmp://")

# 时效性签名参数：URL query 带这些大概率会过期（分钟~小时级）
_SIGNED_URL_RE = re.compile(
    r"[?&](?:auth_key|accountinfo|GuardEncType|SecurityKey|hdnts|wsSecret|txSecret|"
    r"signature|timestamp|expires?|token|signed|sign|sig|st)=",
    re.IGNORECASE,
)

_IPV6_LITERAL_RE = re.compile(r"^[a-z]+://\[[0-9a-fA-F:]+\]", re.IGNORECASE)
# 移动系 CDN（魔百和等）：非移动宽带访问常见 403
CMCC_HOST_RE = re.compile(r"(cmvideo\.cn|chinamobile|cmcc|migu|itv\.cn)", re.IGNORECASE)


def is_signed(url: str) -> bool:
    """带时效签名参数的 URL 视为不稳定（如北京移动 accountinfo、央视 auth_key）。"""
    return bool(_SIGNED_URL_RE.search(url or ""))


def is_ipv6_literal(url: str) -> bool:
    """URL 主机是否为 IPv6 字面量（`http://[2409:...]:6610/...`）。"""
    return bool(_IPV6_LITERAL_RE.match(url or ""))


def is_cmcc_host(url: str) -> bool:
    return bool(CMCC_HOST_RE.search(url or ""))


def level_rank(level: str | None) -> int:
    return LEVEL_RANK.get(str(level or UNKNOWN), UNKNOWN_RANK)


def grade(
    *,
    url: str,
    status: int | None = None,
    body_head: bytes | str = b"",
    error_type: str = "",
    error_msg: str = "",
) -> str:
    """把一次探测结果归类到 LEVEL_RANK 里的一个层级。

    优先级：协议不支持 → 传输层异常 → HTTP 状态码 → 响应体是否像播放列表。
    """
    if not url:
        return UNKNOWN
    if url.lower().startswith(UNPROBEABLE_SCHEMES):
        return RTP

    if error_type:
        et = error_type.lower()
        em = (error_msg or "").lower()
        if "timeout" in et or "timeout" in em or "timed out" in em:
            return TIMEOUT
        if "gaierror" in et or "dns" in et or "name or service not known" in em or "nodename nor servname" in em:
            return DNS_FAIL
        # 注意：aiohttp 的连接错误消息里带 `ssl:default` / `ssl:False`，不能拿 "ssl" 做子串判断
        if "unreachable" in em or "enetunreach" in em:
            return IPV6_NO_ROUTE if is_ipv6_literal(url) else CONN_FAIL
        if "ssl" in et or "certificate" in em or "sslv3" in em or "ssl handshake" in em:
            return SSL_FAIL
        if "disconnect" in et or "connector" in et or "connect" in et or "bad status line" in em:
            return CONN_FAIL
        return CONN_FAIL

    code = int(status or 0)
    if code in (401, 403):
        return HTTP_403
    if code in (404, 410):
        return HTTP_404
    if code >= 400:
        return HTTP_ERROR

    if code in (200, 206):
        return OK if looks_like_playlist(body_head) else PLAYLIST_MISSING
    return HTTP_ERROR


def looks_like_playlist(body_head: bytes | str) -> bool:
    """首片是否像 HLS 播放列表或 MPEG-TS 流。"""
    if isinstance(body_head, str):
        head = body_head.encode("utf-8", "replace")
    else:
        head = body_head or b""
    if not head:
        return False
    if head.startswith(b"\x47"):  # MPEG-TS 同步字节
        return True
    if b"#EXTM3U" in head or b"#EXTINF" in head:
        return True
    return False


def build_index(
    payload: dict[str, Any] | None,
    *,
    max_age_days: int = 7,
    now: datetime | None = None,
) -> dict[str, str]:
    """把 health.json 压成 {url: level}；过期条目标记为 unknown（不参与奖惩）。

    - `payload` 为 None / 结构不对 → 返回空 dict（调用方据此回退旧行为）。
    - 单条超过 `max_age_days` 未探测 → level 降级为 unknown。
    """
    index: dict[str, str] = {}
    if not isinstance(payload, dict):
        return index
    urls = payload.get("urls")
    if not isinstance(urls, dict):
        return index
    ref = now or datetime.now(CST)
    deadline = ref - timedelta(days=max(1, int(max_age_days)))
    for url, rec in urls.items():
        if not url or not isinstance(rec, dict):
            continue
        level = str(rec.get("level") or UNKNOWN)
        checked = _parse_time(rec.get("checked_at"))
        if checked is not None and checked < deadline:
            level = UNKNOWN
        index[str(url)] = level
    return index


def index_age_days(payload: dict[str, Any] | None, *, now: datetime | None = None) -> float | None:
    """health.json 的整体新鲜度（天）。用于过期告警。"""
    if not isinstance(payload, dict):
        return None
    ref = now or datetime.now(CST)
    stamps: list[datetime] = []
    urls = payload.get("urls")
    if isinstance(urls, dict):
        for rec in urls.values():
            if isinstance(rec, dict):
                t = _parse_time(rec.get("checked_at"))
                if t is not None:
                    stamps.append(t)
    if not stamps:
        t = _parse_time(payload.get("generated_at"))
        if t is None:
            return None
        stamps = [t]
    return round((ref - max(stamps)).total_seconds() / 86400, 2)


def summarize(index: dict[str, str]) -> str:
    """一行摘要，如 `ok=29 http-403=41 ...`。"""
    counts: dict[str, int] = {}
    for level in index.values():
        counts[level] = counts.get(level, 0) + 1
    if not counts:
        return "-"
    return " ".join(
        f"{k}={v}" for k, v in sorted(counts.items(), key=lambda kv: (level_rank(kv[0]), kv[0]))
    )


def _parse_time(value: Any) -> datetime | None:
    if not value:
        return None
    text = str(value).strip().replace("Z", "+00:00")
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S"):
        try:
            return datetime.strptime(text, fmt).replace(tzinfo=CST)
        except ValueError:
            continue
    try:
        dt = datetime.fromisoformat(text)
    except ValueError:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=CST)
    return dt