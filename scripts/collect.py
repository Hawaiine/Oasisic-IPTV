# coding: utf-8
"""
Oasisic-IPTV 主采集管线。

流程
----
采集 → 解析 → 清洗 → 匹配 → 分类 → 分组 →（测活）→ 选优 → 写 m3u

环境变量
--------
PROBE_ENABLED : str
    设为 "true" 或 "1" 时启用测活（默认不启用）。
STRICT_SOURCES : str
    设为 "0" 时关闭成功率门禁（默认严格：失败源 ≥30% 则 exit 1）。
"""

from __future__ import annotations

import datetime
import os
import sys
import typing as t

# Ensure scripts/ is on path
_SCRIPTS_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__)))
if _SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, _SCRIPTS_DIR)

import aiohttp
import asyncio

from lib import categories as cat
from lib.classify import classify_by_rules
from lib.clean import clean_channel_name
from lib.io_util import load_yaml, project_root, save_json
from lib.m3u import generate_m3u, parse_m3u_content
from lib.match import match_channel

# ── Config ─────────────────────────────────────────────────────────

_PROBE_ENABLED = os.environ.get("PROBE_ENABLED", "").lower() in ("true", "1")
_STRICT_SOURCES = os.environ.get("STRICT_SOURCES", "1") not in ("0", "false", "no")


def _load_settings() -> dict:
    return load_yaml(os.path.join(project_root(), "config", "settings.yaml"))


def _load_sources() -> list[dict]:
    data = load_yaml(os.path.join(project_root(), "config", "sources.yaml"))
    return data.get("sources", [])


# ── Fetch ──────────────────────────────────────────────────────────


async def _fetch_source(
    session: aiohttp.ClientSession,
    source: dict,
    timeout: int,
    user_agent: str,
) -> tuple[str, str, str]:
    """Fetch a single source. Returns (name, url, content_or_error)."""
    name: str = source["name"]
    url: str = source["url"]
    headers = {"User-Agent": user_agent}
    try:
        async with session.get(url, timeout=aiohttp.ClientTimeout(total=timeout)) as resp:
            if resp.status != 200:
                return name, url, f"HTTP {resp.status}"
            text = await resp.text(encoding="utf-8", errors="replace")
            return name, url, text
    except Exception as exc:
        return name, url, f"ERROR: {exc}"


async def _fetch_all(sources: list[dict], settings: dict) -> list[dict]:
    """Fetch all enabled sources concurrently."""
    timeout = settings.get("request_timeout_sec", 30)
    user_agent = settings.get(
        "user_agent",
        "Mozilla/5.0 (compatible; Oasisic-IPTV/1.0)",
    )
    enabled = [s for s in sources if s.get("enabled", True)]
    connector = aiohttp.TCPConnector(limit_per_host=3)
    async with aiohttp.ClientSession(connector=connector) as session:
        tasks = [_fetch_source(session, s, timeout, user_agent) for s in enabled]
        results = await asyncio.gather(*tasks)
    out: list[dict] = []
    for source, (name, url, content) in zip(enabled, results):
        out.append({"name": name, "url": url, "content": content})
    return out


# ── Pipeline stages ────────────────────────────────────────────────


def _is_error(content: str) -> bool:
    return content.startswith("HTTP ") or content.startswith("ERROR:")


def _parse_all(fetched: list[dict]) -> list[dict]:
    """Parse M3U content from all fetched sources into channel dicts."""
    all_channels: list[dict] = []
    for entry in fetched:
        content = entry["content"]
        if _is_error(content):
            continue
        channels = parse_m3u_content(content, entry["name"])
        all_channels.extend(channels)
    return all_channels


def _clean_all(channels: list[dict]) -> list[dict]:
    """Clean channel names in-place, removing entries that become None."""
    out: list[dict] = []
    for ch in channels:
        cleaned = clean_channel_name(ch.get("name", ""))
        if cleaned:
            ch["name"] = cleaned
            out.append(ch)
    return out


def _match_and_classify(channels: list[dict]) -> list[dict]:
    """
    Match against standard table; fallback to keyword classification.

    After this step every channel has:
      - category
      - group_title (canonical from categories module)
      - standard_name (if matched, else "")
    """
    for ch in channels:
        m = match_channel(ch["name"])
        if m:
            ch["category"] = m["category"]
            ch["standard_name"] = m["standard_name"]
            ch["group_title"] = cat.group_title(m["category"])
            if not ch.get("tvg_id"):
                ch["tvg_id"] = m.get("tvg_id", "")
        else:
            # Fallback: keyword classification
            src_grp = ch.get("group_title", "")
            cat_key, grp_title = classify_by_rules(ch["name"], src_grp)
            ch["category"] = cat_key
            ch["standard_name"] = ""
            ch["group_title"] = grp_title
    return channels


def _group_by_category(channels: list[dict]) -> dict[str, list[dict]]:
    """Group channels by category key."""
    groups: dict[str, list[dict]] = {}
    for ch in channels:
        key = ch.get("category", "other")
        groups.setdefault(key, []).append(ch)
    return groups


def _select_best(
    groups: dict[str, list[dict]], max_keep: int
) -> dict[str, list[dict]]:
    """Select at most ``max_keep`` channels per standard_name within each
    category.  When probe is disabled all channels are considered alive,
    so we take the first N unique URLs per standard name."""
    selected: dict[str, list[dict]] = {}
    for key, ch_list in groups.items():
        seen: dict[str, list[dict]] = {}
        for ch in ch_list:
            std = ch.get("standard_name") or ch.get("name", "?")
            seen.setdefault(std, []).append(ch)
        chosen: list[dict] = []
        for _std, entries in seen.items():
            chosen.extend(entries[:max_keep])
        selected[key] = chosen
    return selected


# ── Main ───────────────────────────────────────────────────────────


def main() -> None:
    settings = _load_settings()
    sources = _load_sources()
    max_keep = settings.get("max_keep_per_channel", 2)
    output_dir = settings.get("output_dir", "output/")
    output_abs = os.path.join(project_root(), output_dir)
    os.makedirs(output_abs, exist_ok=True)

    # ── 1. Fetch ───────────────────────────────────────────────
    print("🌐 采集源 ...")
    fetched = asyncio.run(_fetch_all(sources, settings))
    enabled = [s for s in sources if s.get("enabled", True)]
    total_enabled = len(enabled)
    ok_count = 0
    for entry in fetched:
        if _is_error(entry["content"]):
            print(f"   ❌ {entry['name']}: {entry['content']}")
        else:
            ok_count += 1
    success_rate = (ok_count / total_enabled * 100) if total_enabled else 0
    print(f"   成功: {ok_count}/{total_enabled} ({success_rate:.0f}%)")
    if _STRICT_SOURCES and success_rate < 70:
        print(f"❌ 源成功率 {success_rate:.0f}% < 70%，退出")
        sys.exit(1)

    # ── 2. Parse ───────────────────────────────────────────────
    print("📄 解析 M3U ...")
    parsed = _parse_all(fetched)
    print(f"   {len(parsed)} 条原始频道")

    # ── 3. Clean ───────────────────────────────────────────────
    print("🧹 清洗名称 ...")
    cleaned = _clean_all(parsed)
    print(f"   {len(cleaned)} 条清洗后")

    # ── 4. Match + Classify ────────────────────────────────────
    print("🔗 匹配/分类 ...")
    matched = _match_and_classify(cleaned)
    matched_cnt = sum(1 for ch in matched if ch.get("standard_name"))
    classified_cnt = len(matched) - matched_cnt
    print(f"   {matched_cnt} 条标准表匹配 + {classified_cnt} 条规则分类")

    # ── 5. Group ───────────────────────────────────────────────
    print("📂 分组 ...")
    groups = _group_by_category(matched)
    total_in_groups = sum(len(v) for v in groups.values())
    print(f"   {total_in_groups} 条已分组")
    for key, ch_list in sorted(groups.items()):
        print(f"     {key}: {len(ch_list)}")

    # ── 6. (Probe) — stubbed ───────────────────────────────────
    if _PROBE_ENABLED:
        print("📡 测活启用（Phase5 完整实现，当前跳过）")

    # ── 7. Select ──────────────────────────────────────────────
    print(f"🎯 选优 (max_keep={max_keep}) ...")
    selected = _select_best(groups, max_keep)
    total_selected = sum(len(v) for v in selected.values())
    print(f"   {total_selected} 条选优后")

    # ── 8. Write M3U ───────────────────────────────────────────
    print("💾 写 M3U ...")

    # Normalize group_title for every channel: map category → canonical title
    for key, ch_list in selected.items():
        canonical = cat.group_title(key)
        for ch in ch_list:
            ch["group_title"] = canonical

    # Main live.m3u: follow categories.iter_main_order(), exclude radio
    main_order = list(cat.iter_main_order())
    main_channels: list[dict] = []
    for key in main_order:
        if key in selected:
            for ch in selected[key]:
                main_channels.append({**ch, "group_title": cat.group_title(key)})

    generate_m3u(main_channels, os.path.join(output_abs, "live.m3u"), "Oasisic-IPTV")
    print(f"   live.m3u: {len(main_channels)} 条")

    # Category files (exclude radio — handled separately)
    cat_files_written = 0
    for key, ch_list in selected.items():
        if cat.is_radio(key):
            continue
        filename = cat.file_for(key)
        cat_channels = [{**ch, "group_title": cat.group_title(key)} for ch in ch_list]
        generate_m3u(
            cat_channels,
            os.path.join(output_abs, filename),
            f"Oasisic-IPTV - {cat.title_for(key)}",
        )
        cat_files_written += 1

    # Radio
    radio_key = cat.RADIO_KEY
    if radio_key in selected:
        radio_list = [{**ch, "group_title": cat.group_title(radio_key)} for ch in selected[radio_key]]
        generate_m3u(
            radio_list,
            os.path.join(output_abs, cat.file_for(radio_key)),
            "Oasisic-IPTV - 电台",
        )
        print(f"   {cat.file_for(radio_key)}: {len(radio_list)} 条")

    print(f"   分类文件: {cat_files_written} 个类别")

    # ── 9. Write check_result.json ─────────────────────────────
    now = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=8)))
    check = {
        "schema_version": 1,
        "stage": "collect",
        "generated_at": now.strftime("%Y-%m-%d %H:%M:%S"),
        "timezone": "Asia/Shanghai",
        "total": total_selected,
        "ok": 0,
        "fail": 0,
        "ratio": 0.0,
        "probe_enabled": _PROBE_ENABLED,
        "channels": [],
    }
    check_path = os.path.join(output_abs, "check_result.json")
    save_json(check_path, check)

    # ── Summary ────────────────────────────────────────────────
    print()
    print("=" * 40)
    print(f"✅ 采集完成 (probe_enabled={_PROBE_ENABLED})")
    print(f"   总输出: {total_selected} 条")
    print(f"   源成功率: {ok_count}/{total_enabled} ({success_rate:.0f}%)")
    print(f"   check_result.json → {check_path}")
    print("=" * 40)


if __name__ == "__main__":
    main()