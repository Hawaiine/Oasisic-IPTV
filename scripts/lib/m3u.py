"""M3U / TXT 播放列表解析与生成。"""

from __future__ import annotations

import re
from typing import Any

DEFAULT_URL_TVG = "https://live.fanmingming.com/e.xml"

_ATTR_RE = re.compile(r'([A-Za-z0-9-]+)="([^"]*)"')
_EXTINF_PREFIX = "#EXTINF:"


def parse_extinf_attrs(info: str) -> dict[str, str]:
    return {k: v for k, v in _ATTR_RE.findall(info)}


def split_extinf(payload: str) -> tuple[str, str]:
    """引号感知切分 EXTINF：返回 (属性区, 名称)。

    旧的 `r"#EXTINF:([^,]*),(.*)$"` 在第一个逗号处切分，上游两种畸形写法会把
    属性原文塞进频道名：
    1. 属性值里带逗号（`http-user-agent="Mozilla/5.0 … like Gecko) Chrome/149"`）；
    2. 属性块重复（`#EXTINF:-1 group-title="X",tvg-id="Y" group-title="Z",名称`）。
    这里按引号状态找第一个「不在引号内」的逗号。
    """
    in_quote = False
    for i, ch in enumerate(payload):
        if ch == '"':
            in_quote = not in_quote
        elif ch == "," and not in_quote:
            return payload[:i], payload[i + 1 :]
    return payload, ""


def clean_leaked_name(name: str) -> str:
    """名称里混入属性原文时，取最后一个 `",` 之后的真实名称。"""
    text = (name or "").strip()
    if '="' not in text:
        return text
    idx = text.rfind('",')
    if idx != -1:
        return text[idx + 2 :].strip()
    return text


def parse_m3u(text: str) -> list[dict[str, Any]]:
    """解析 M3U，返回 {name, url, group, tvg_id, tvg_logo, attrs}。"""
    entries: list[dict[str, Any]] = []
    lines = text.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    pending: dict[str, Any] | None = None
    for raw in lines:
        line = raw.strip()
        if not line:
            continue
        if line.startswith(_EXTINF_PREFIX):
            payload = line[len(_EXTINF_PREFIX) :]
            _head, raw_name = split_extinf(payload)
            attrs = parse_extinf_attrs(payload)
            name = clean_leaked_name(raw_name)
            pending = {
                "name": name,
                "url": "",
                "group": attrs.get("group-title", ""),
                "tvg_id": attrs.get("tvg-id", ""),
                "tvg_logo": attrs.get("tvg-logo", ""),
                "attrs": attrs,
            }
            continue
        if line.startswith("#"):
            continue
        if pending is not None:
            pending["url"] = line
            if pending["name"] and pending["url"]:
                entries.append(pending)
            pending = None
        else:
            continue
    return entries


def parse_txt(text: str) -> list[dict[str, Any]]:
    """解析 名称,URL 或 分类,#genre# / 名称,URL 格式。"""
    entries: list[dict[str, Any]] = []
    group = ""
    for raw in text.replace("\r\n", "\n").split("\n"):
        line = raw.strip()
        if not line or line.startswith("#") and not line.endswith("#genre#"):
            if line.endswith("#genre#"):
                group = line.replace("#genre#", "").strip().rstrip(",")
            continue
        if line.endswith("#genre#"):
            group = line.replace("#genre#", "").strip().rstrip(",")
            continue
        if "," not in line:
            continue
        name, url = line.split(",", 1)
        name, url = name.strip(), url.strip()
        if not name or not url or not (
            url.startswith("http") or url.startswith("rtp://") or url.startswith("rtsp://")
        ):
            continue
        entries.append(
            {
                "name": name,
                "url": url,
                "group": group,
                "tvg_id": "",
                "tvg_logo": "",
                "attrs": {},
            }
        )
    return entries


def parse_playlist(text: str, source_type: str = "m3u") -> list[dict[str, Any]]:
    stripped = text.lstrip()
    if source_type == "txt" or (
        source_type != "m3u" and not stripped.startswith("#EXTM3U") and "#EXTINF" not in text[:2000]
    ):
        return parse_txt(text)
    return parse_m3u(text)


def format_extinf(
    *,
    name: str,
    group: str,
    tvg_id: str = "",
    tvg_logo: str = "",
    duration: int = -1,
) -> str:
    parts = [f"#EXTINF:{duration}"]
    if tvg_id:
        parts.append(f'tvg-id="{tvg_id}"')
    if tvg_logo:
        parts.append(f'tvg-logo="{tvg_logo}"')
    if group:
        parts.append(f'group-title="{group}"')
    return " ".join(parts) + f",{name}"


def build_m3u(
    entries: list[dict[str, Any]],
    *,
    playlist_title: str = "Oasisic-IPTV",
    url_tvg: str = DEFAULT_URL_TVG,
    use_epg_id: bool = True,
) -> str:
    """生成 M3U。`use_epg_id=True` 时 `tvg-id = epg_id or tvg_id`（回退保证零退化）。"""
    header = "#EXTM3U"
    if url_tvg:
        header = f'#EXTM3U url-tvg="{url_tvg}"'
    lines = [header, f"#PLAYLIST:{playlist_title}"]
    for e in entries:
        tid = ""
        if use_epg_id:
            tid = e.get("epg_id") or e.get("tvg_id") or ""
        else:
            tid = e.get("tvg_id") or ""
        lines.append(
            format_extinf(
                name=e.get("display_name") or e.get("name") or "",
                group=e.get("group_title") or e.get("group") or "",
                tvg_id=tid,
                tvg_logo=e.get("tvg_logo") or "",
            )
        )
        lines.append(e.get("url") or "")
    lines.append("")
    return "\n".join(lines)


def build_txt(
    entries: list[dict[str, Any]],
    *,
    use_epg_id: bool = False,
    include_header: bool = False,
) -> str:
    """生成 TXT 播放列表（TVBox / DIYP / 影视仓系）。

    格式：`分组,#genre#` 分段，段内 `名称,URL`。分组用中文 group-title，
    与 M3U 完全同口径；`use_epg_id` 仅用于把 `名称` 里附上 tvg-id 供部分壳子对 EPG。
    """
    lines: list[str] = []
    if include_header:
        lines.append("# Oasisic-IPTV TXT 播放列表（分组,#genre# 分段）")
    current = None
    for e in entries:
        group = e.get("group_title") or e.get("group") or "其他"
        if group != current:
            if current is not None:
                lines.append("")
            lines.append(f"{group},#genre#")
            current = group
        name = e.get("display_name") or e.get("name") or ""
        url = e.get("url") or ""
        if not name or not url:
            continue
        if use_epg_id:
            tid = e.get("epg_id") or e.get("tvg_id") or ""
            if tid:
                name = f"{name} (${tid})"
        lines.append(f"{name},{url}")
    return "\n".join(lines) + "\n"


def count_entries(text: str) -> int:
    return sum(1 for line in text.splitlines() if line.startswith("#EXTINF"))
