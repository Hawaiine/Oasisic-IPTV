"""EPG 上游工具：拉取、id 解析、epg_id 选取规则（纯函数 + 一个 aiohttp 拉取器）。

设计要点：
- 多源**真合并**：所有源都拉，失败逐个报错，不再「第一个成功就 break」。
- `epg_id` 必须能在一个上游里原样命中，且该 id 在指南里**确实有 programme**；
  否则写 null 并列进 `data/epg_missing.txt`（禁止臆造、禁止近似台顶替）。
"""

from __future__ import annotations

import gzip
import re
from collections import Counter
from typing import Any, Iterable

_CHANNEL_RE = re.compile(r'<channel id="([^"]+)"')
_CHANNEL_BLOCK_RE = re.compile(r'<channel id="([^"]+)">(.*?)</channel>', re.S)
_DISPLAY_NAME_RE = re.compile(r"<display-name[^>]*>([^<]*)</display-name>")
_PROG_RE = re.compile(r'<programme[^>]*\bchannel="([^"]+)"')


async def fetch_upstreams(urls: Iterable[str], *, timeout: int = 120, ua: str = "Oasisic-IPTV/1.0") -> list[tuple[str, str | None, str]]:
    """并发拉取全部上游；返回 [(url, text|None, error)]，失败的 text 为 None。"""
    import asyncio

    import aiohttp

    async def one(session: Any, url: str) -> tuple[str, str | None, str]:
        try:
            async with session.get(
                url,
                timeout=aiohttp.ClientTimeout(total=timeout),
                headers={"User-Agent": ua, "Accept-Encoding": "gzip, deflate"},
            ) as resp:
                if resp.status != 200:
                    return (url, None, f"HTTP {resp.status}")
                raw = await resp.read()
                if raw[:2] == b"\x1f\x8b":
                    raw = gzip.decompress(raw)
                return (url, raw.decode("utf-8", "replace"), "")
        except Exception as exc:  # noqa: BLE001
            return (url, None, f"{type(exc).__name__}: {str(exc)[:120]}")

    connector = aiohttp.TCPConnector(ssl=False)
    async with aiohttp.ClientSession(connector=connector) as session:
        return await asyncio.gather(*(one(session, u) for u in urls))


def parse_channel_ids(text: str) -> list[str]:
    return _CHANNEL_RE.findall(text)


def parse_channels_with_names(text: str) -> dict[str, list[str]]:
    """解析 id → display-name 列表（有些上游 id 是纯数字，只能靠名字对齐）。"""
    out: dict[str, list[str]] = {}
    for cid, body in _CHANNEL_BLOCK_RE.findall(text):
        names = [n.strip() for n in _DISPLAY_NAME_RE.findall(body) if n.strip()]
        out[cid] = names
    return out


def parse_programme_counts(text: str) -> Counter[str]:
    return Counter(_PROG_RE.findall(text))


def choose_epg_id(
    channel: dict[str, Any],
    *,
    ids_all: set[str],
    ids_with_programme: set[str],
    aliases: dict[str, list[str]] | None = None,
    name_index: dict[str, str] | None = None,
) -> tuple[str | None, str]:
    """按 tvg_id → display_name → standard_name → 别名 的顺序挑 epg_id。

    两级匹配：
    1. **id 直配**：候选字符串本身就是上游 id（央视 `CCTV1`、卫视中文名…）。
    2. **名字直配**：上游 id 是数字（epg.pw 等），用 display-name 反查 id。
    两级都要求「该 id 在上游有 programme」；否则返回 (None, 原因)。
    """
    std = str(channel.get("standard_name") or "")
    candidates: list[tuple[str, str]] = []
    for field in ("tvg_id", "display_name", "standard_name"):
        val = str(channel.get(field) or "").strip()
        if val:
            candidates.append((val, field))
    for alias in (aliases or {}).get(std, []) or []:
        alias = str(alias).strip()
        if alias:
            candidates.append((alias, "alias"))

    seen: set[str] = set()
    ordered: list[tuple[str, str]] = []
    for val, src in candidates:
        if val not in seen:
            seen.add(val)
            ordered.append((val, src))

    for val, src in ordered:
        if val in ids_with_programme:
            return val, f"matched:{src}"
    for val, src in ordered:
        cid = (name_index or {}).get(val)
        if cid and cid in ids_with_programme:
            return cid, f"matched-name:{src}->{val}"

    present = [v for v, _ in ordered if v in ids_all]
    if present:
        return None, f"upstream-no-programme:{present[0]}"
    return None, "upstream-missing"


def build_missing_report(
    channels: list[dict[str, Any]],
    *,
    ids_all: set[str],
    ids_with_programme: set[str],
    aliases: dict[str, list[str]] | None = None,
    name_index: dict[str, str] | None = None,
) -> tuple[dict[str, dict[str, Any]], list[str]]:
    """返回 (standard_name → {epg_id, reason}, 缺失行文本列表)。"""
    mapping: dict[str, dict[str, Any]] = {}
    missing: list[str] = []
    for ch in channels:
        epg_id, reason = choose_epg_id(
            ch,
            ids_all=ids_all,
            ids_with_programme=ids_with_programme,
            aliases=aliases,
            name_index=name_index,
        )
        mapping[ch["standard_name"]] = {"epg_id": epg_id, "reason": reason}
        if epg_id is None:
            missing.append(f"{ch['standard_name']} | {ch.get('category', '')} | {reason}")
    return mapping, missing


def load_epg_ids(channels: list[dict[str, Any]]) -> set[str]:
    """选优/裁剪用的 epg_id 集合（含 tvg_id 回退口径）。"""
    out: set[str] = set()
    for ch in channels:
        for key in ("epg_id", "tvg_id"):
            val = str(ch.get(key) or "").strip()
            if val:
                out.add(val)
    return out