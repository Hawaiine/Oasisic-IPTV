"""M3U / TXT 播放列表解析与生成。"""

from __future__ import annotations

import re
from typing import Any

DEFAULT_URL_TVG = "https://live.fanmingming.com/e.xml"

_EXTINF_RE = re.compile(
    r"#EXTINF:([^,]*),(.*)$",
)
_ATTR_RE = re.compile(r'([A-Za-z0-9-]+)="([^"]*)"')


def parse_extinf_attrs(info: str) -> dict[str, str]:
    return {k: v for k, v in _ATTR_RE.findall(info)}


def parse_m3u(text: str) -> list[dict[str, Any]]:
    """解析 M3U，返回 {name, url, group, tvg_id, tvg_logo, attrs}。"""
    entries: list[dict[str, Any]] = []
    lines = text.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    pending: dict[str, Any] | None = None
    for raw in lines:
        line = raw.strip()
        if not line:
            continue
        if line.startswith("#EXTINF:"):
            m = _EXTINF_RE.match(line)
            duration_and_attrs = m.group(1) if m else ""
            name = (m.group(2) if m else "").strip()
            attrs = parse_extinf_attrs(duration_and_attrs)
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
) -> str:
    header = "#EXTM3U"
    if url_tvg:
        header = f'#EXTM3U url-tvg="{url_tvg}"'
    lines = [header, f"#PLAYLIST:{playlist_title}"]
    for e in entries:
        lines.append(
            format_extinf(
                name=e.get("display_name") or e.get("name") or "",
                group=e.get("group_title") or e.get("group") or "",
                tvg_id=e.get("tvg_id") or "",
                tvg_logo=e.get("tvg_logo") or "",
            )
        )
        lines.append(e.get("url") or "")
    lines.append("")
    return "\n".join(lines)


def count_entries(text: str) -> int:
    return sum(1 for line in text.splitlines() if line.startswith("#EXTINF"))
