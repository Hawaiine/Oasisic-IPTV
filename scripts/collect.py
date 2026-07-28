# coding: utf-8
"""
Oasisic-IPTV 主采集管线。

流程
----
采集 → 解析 → 清洗 → 匹配 → 分类 → 分组 → 测活 → 选优 → 写 m3u

环境变量
--------
PROBE_ENABLED : str
PROBE_CONCURRENCY : int
PROBE_TIMEOUT : int
MAX_KEEP_PER_CHANNEL : int
PROBE_REGION : str
STRICT_SOURCES : str
"""

from __future__ import annotations

import datetime
import os
import re
import sys
import typing as t

_SCRIPTS_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__)))
if _SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, _SCRIPTS_DIR)

import aiohttp
import asyncio

from lib import categories as cat
from lib.classify import classify_by_rules
from lib.clean import clean_channel_name
from lib.io_util import load_yaml, project_root, save_json
from lib.m3u import generate_m3u, parse_m3u_content, parse_txt_content
from lib.match import match_channel

_PROBE_ENABLED = os.environ.get("PROBE_ENABLED", "").lower() in ("true", "1")
_PROBE_CONCURRENCY = int(os.environ.get("PROBE_CONCURRENCY", "10"))
_PROBE_TIMEOUT = int(os.environ.get("PROBE_TIMEOUT", "10"))
_PROBE_REGION = os.environ.get("PROBE_REGION", "wuhan-unicom")
_MAX_KEEP_ENV = os.environ.get("MAX_KEEP_PER_CHANNEL", "")
_STRICT_SOURCES = os.environ.get("STRICT_SOURCES", "1") not in ("0", "false", "no")

_CORE_SOURCE_NAMES: set[str] = {
    "fanmingming-ipv6", "yuechan-cn", "guovin-iptv-api",
    "iptv-org-cn", "iptv-org-hk", "iptv-org-tw",
}

# Source region priority (lower = preferred for stable sort without probe)
_SOURCE_PRIORITY: dict[str, int] = {
    "cn": 0,
    "hk_tw": 1,
    "hotel": 2,
    "overseas": 3,
}


def _load_settings() -> dict:
    return load_yaml(os.path.join(project_root(), "config", "settings.yaml"))


def _load_sources() -> list[dict]:
    data = load_yaml(os.path.join(project_root(), "config", "sources.yaml"))
    return data.get("sources", [])


async def _fetch_source(
    session: aiohttp.ClientSession, source: dict, timeout: int, user_agent: str,
) -> tuple[str, str, str, str]:
    name: str = source["name"]
    url: str = source["url"]
    src_type: str = source.get("type", "m3u")
    headers = {"User-Agent": user_agent}
    try:
        async with session.get(url, timeout=aiohttp.ClientTimeout(total=timeout)) as resp:
            if resp.status != 200:
                return name, url, src_type, f"HTTP {resp.status}"
            text = await resp.text(encoding="utf-8", errors="replace")
            return name, url, src_type, text
    except Exception as exc:
        return name, url, src_type, f"ERROR: {exc}"


async def _fetch_all(sources: list[dict], settings: dict) -> list[dict]:
    timeout = settings.get("request_timeout_sec", 30)
    user_agent = settings.get("user_agent", "Mozilla/5.0 (compatible; Oasisic-IPTV/1.0)")
    enabled = [s for s in sources if s.get("enabled", True)]
    connector = aiohttp.TCPConnector(limit_per_host=3)
    async with aiohttp.ClientSession(connector=connector) as session:
        tasks = [_fetch_source(session, s, timeout, user_agent) for s in enabled]
        results = await asyncio.gather(*tasks)
    out: list[dict] = []
    for source, (name, url, stype, content) in zip(enabled, results):
        out.append({"name": name, "url": url, "type": stype, "region": source.get("region", "cn"), "content": content})
    return out


def _is_error(content: str) -> bool:
    return content.startswith("HTTP ") or content.startswith("ERROR:")


def _parse_all(fetched: list[dict]) -> list[dict]:
    all_channels: list[dict] = []
    for entry in fetched:
        content = entry["content"]
        if _is_error(content):
            continue
        if entry.get("type") == "txt":
            channels = parse_txt_content(content, entry["name"])
        else:
            channels = parse_m3u_content(content, entry["name"])
        for ch in channels:
            ch["source_region"] = entry.get("region", "cn")
        all_channels.extend(channels)
    return all_channels


def _clean_all(channels: list[dict]) -> list[dict]:
    out: list[dict] = []
    for ch in channels:
        cleaned = clean_channel_name(ch.get("name", ""))
        if cleaned:
            ch["name"] = cleaned
            out.append(ch)
    return out


def _match_and_classify(channels: list[dict]) -> list[dict]:
    """
    Match against standard table → classify with display name rule.

    Display name priority:
      1. standard_name (Chinese) if matched
      2. cleaned name otherwise
    """
    for ch in channels:
        m = match_channel(ch["name"])
        if m:
            ch["category"] = m["category"]
            ch["standard_name"] = m["standard_name"]
            ch["group_title"] = cat.group_title(m["category"])
            # Display name: use standard_name (Chinese) as output name
            ch["name"] = m.get("display_name") or m["standard_name"]
            if not ch.get("tvg_id"):
                ch["tvg_id"] = m.get("tvg_id", "")
        else:
            src_grp = ch.get("group_title", "")
            region = ch.get("source_region", "cn")

            # Source region override
            if region == "hotel":
                ch["category"] = "special"
                ch["standard_name"] = ""
                ch["group_title"] = cat.group_title("special")
            elif region == "overseas":
                cat_key, grp_title = classify_by_rules(ch["name"], src_grp)
                # If the name is clearly Chinese, keep the classify result
                # Otherwise, overseas sources stay overseas
                has_cn = bool(re.search(r"[\u4e00-\u9fff]", ch["name"]))
                if has_cn and cat_key != "overseas":
                    ch["category"] = cat_key
                    ch["group_title"] = grp_title
                else:
                    ch["category"] = "overseas"
                    ch["group_title"] = cat.group_title("overseas")
                ch["standard_name"] = ""
            else:
                cat_key, grp_title = classify_by_rules(ch["name"], src_grp)
                ch["category"] = cat_key
                ch["standard_name"] = ""
                ch["group_title"] = grp_title
    return channels


def _group_by_category(channels: list[dict]) -> dict[str, list[dict]]:
    groups: dict[str, list[dict]] = {}
    for ch in channels:
        key = ch.get("category", "other")
        groups.setdefault(key, []).append(ch)
    return groups


def _select_best(groups: dict[str, list[dict]], max_keep: int) -> dict[str, list[dict]]:
    """
    Per-category selection + global dedup.

    1. Within each category, group by name key, keep max_keep per name.
    2. Sort by source_region priority (cn→hk_tw→hotel→overseas), then latency.
       rtp:// URLs are penalized (sorted last regardless of region).
    3. URL dedup within each category.
    4. Global dedup: merge same-name channels across categories, keep max_keep.
    5. Global URL dedup: same URL → keep highest-priority entry (non-radio wins).
    6. Radio is isolated (not merged with other categories).
    """
    def _sort_key(ch: dict) -> tuple:
        """Sort key: region priority, rtp penalty, latency."""
        region = _SOURCE_PRIORITY.get(ch.get("source_region", "cn"), 99)
        url = ch.get("url", "")
        rtp_penalty = 1 if url.lower().startswith("rtp://") else 0
        return (region, rtp_penalty, ch.get("latency_ms", 999999))

    # ── Step 1-3: Per-category selection ──────────────────────
    selected: dict[str, list[dict]] = {}
    for key, ch_list in groups.items():
        seen: dict[str, list[dict]] = {}
        for ch in ch_list:
            if ch.get("alive") is False:
                continue
            std = ch.get("standard_name") or ch.get("name", "?")
            seen.setdefault(std, []).append(ch)

        chosen: list[dict] = []
        for _std, entries in seen.items():
            sorted_entries = sorted(entries, key=_sort_key)
            chosen.extend(sorted_entries[:max_keep])

        # URL dedup within category
        cat_dedup: list[dict] = []
        cat_seen_urls: set[str] = set()
        for ch in chosen:
            url = ch.get("url", "")
            if url and url in cat_seen_urls:
                continue
            cat_seen_urls.add(url)
            cat_dedup.append(ch)
        selected[key] = cat_dedup

    # ── Step 4: Global dedup across categories by name ────────
    global_by_name: dict[str, list[dict]] = {}
    for key, ch_list in selected.items():
        if key == "radio":
            continue
        for ch in ch_list:
            nk = ch.get("standard_name") or ch.get("name", "?")
            global_by_name.setdefault(nk, []).append(ch)

    global_selected: dict[str, list[dict]] = {}
    for key in selected:
        if key == "radio":
            global_selected[key] = selected[key]
        else:
            global_selected[key] = []

    for nk, ch_list in global_by_name.items():
        ch_list.sort(key=_sort_key)
        kept = ch_list[:max_keep]
        for ch in kept:
            key = ch.get("category", "other")
            if key == "radio":
                continue
            global_selected.setdefault(key, []).append(ch)

    # ── Step 5: Global URL dedup (non-radio wins) ─────────────
    url_taken: dict[str, dict] = {}
    url_duplicate_count = 0

    for key, ch_list in list(global_selected.items()):
        if key == "radio":
            continue
        deduped: list[dict] = []
        for ch in ch_list:
            url = ch.get("url", "")
            if not url:
                deduped.append(ch)
                continue
            if url in url_taken:
                url_duplicate_count += 1
                existing = url_taken[url]
                if _sort_key(ch) < _sort_key(existing):
                    url_taken[url] = ch
            else:
                url_taken[url] = ch
                deduped.append(ch)
        global_selected[key] = deduped

    if "radio" in global_selected:
        radio_deduped: list[dict] = []
        for ch in global_selected["radio"]:
            url = ch.get("url", "")
            if url and url in url_taken:
                url_duplicate_count += 1
                continue
            radio_deduped.append(ch)
        global_selected["radio"] = radio_deduped

    if url_duplicate_count:
        print(f"   🔗 全局 URL 去重: 移除 {url_duplicate_count} 条重复")

    return global_selected


def _split_catalog_more(selected: dict[str, list[dict]], main_include_overseas: bool) -> tuple[dict[str, list[dict]], list[dict]]:
    """
    Split selected channels into catalog (has standard_name) and more (no standard_name).

    Returns:
      catalog: dict[str, list[dict]] — for live.m3u and category files
      more: list[dict] — for live_more.m3u
    """
    catalog: dict[str, list[dict]] = {}
    more: list[dict] = []
    more_order = list(cat.iter_main_order())

    for key, ch_list in selected.items():
        if key == "radio":
            catalog[key] = ch_list
            continue
        if key == "overseas" and not main_include_overseas:
            # Overseas only goes to catalog if explicitly included
            # Otherwise, still add to more (but more is mainly domestic)
            catalog[key] = []
            continue

        cat_catalog: list[dict] = []
        cat_more: list[dict] = []
        for ch in ch_list:
            if ch.get("standard_name"):
                cat_catalog.append(ch)
            else:
                cat_more.append(ch)

        catalog[key] = cat_catalog
        more.extend(cat_more)

    # Sort more by category order
    def _more_sort_key(ch: dict) -> tuple:
        try:
            return (more_order.index(ch.get("category", "other")), ch.get("name", ""))
        except ValueError:
            return (999, ch.get("name", ""))

    more.sort(key=_more_sort_key)

    return catalog, more


def main() -> None:
    settings = _load_settings()
    sources = _load_sources()
    max_keep = int(_MAX_KEEP_ENV) if _MAX_KEEP_ENV else settings.get("max_keep_per_channel", 1)
    catalog_only = settings.get("catalog_only_main", True)
    write_more = settings.get("write_live_more", True)
    more_max = settings.get("more_max_channels", 3000)
    main_include_overseas = settings.get("main_include_overseas", False)
    output_dir = settings.get("output_dir", "output/")
    output_abs = os.path.join(project_root(), output_dir)
    os.makedirs(output_abs, exist_ok=True)

    # ── 1. Fetch ───────────────────────────────────────────────
    print("🌐 采集源 ...")
    fetched = asyncio.run(_fetch_all(sources, settings))
    enabled = [s for s in sources if s.get("enabled", True)]
    total_enabled = len(enabled)
    ok_count = 0
    core_ok = 0
    core_total = 0
    for entry in fetched:
        is_core = entry["name"] in _CORE_SOURCE_NAMES
        if _is_error(entry["content"]):
            print(f"   ❌ {entry['name']}: {entry['content']}")
        else:
            ok_count += 1
            if is_core:
                core_ok += 1
        if is_core:
            core_total += 1
    success_rate = (ok_count / total_enabled * 100) if total_enabled else 0
    print(f"   成功: {ok_count}/{total_enabled} ({success_rate:.0f}%)")
    if _STRICT_SOURCES and core_total > 0:
        if core_ok < core_total:
            print(f"❌ 核心源成功率 {core_ok}/{core_total} < 100%，退出")
            sys.exit(1)
        print(f"   ✅ 核心源 {core_ok}/{core_total} 全部成功")

    # ── 2. Parse ───────────────────────────────────────────────
    print("📄 解析 ...")
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

    # ── 6. Probe ───────────────────────────────────────────────
    probe_ok = 0
    probe_fail = 0
    if _PROBE_ENABLED:
        from lib.probe import probe_channels
        print("📡 测活中 ...")
        matched = asyncio.run(
            probe_channels(matched, concurrency=_PROBE_CONCURRENCY, timeout=_PROBE_TIMEOUT)
        )
        probe_ok = sum(1 for ch in matched if ch.get("alive"))
        probe_fail = sum(1 for ch in matched if not ch.get("alive"))
        print(f"   ✅ {probe_ok} 可用, ❌ {probe_fail} 不可用")
    else:
        for ch in matched:
            ch["alive"] = True

    # ── 7. Select ──────────────────────────────────────────────
    print(f"🎯 选优 (max_keep={max_keep}) ...")
    selected = _select_best(groups, max_keep)
    total_selected = sum(len(v) for v in selected.values())
    print(f"   {total_selected} 条选优后")

    # ── 8. Split catalog vs more ───────────────────────────────
    catalog, more = _split_catalog_more(selected, main_include_overseas)
    catalog_total = sum(len(v) for v in catalog.values())
    print(f"📋 目录分流: catalog={catalog_total} / more={len(more)}")

    # ── 9. Write M3U ───────────────────────────────────────────
    print("💾 写 M3U ...")

    # Normalize group_title
    for key, ch_list in catalog.items():
        canonical = cat.group_title(key)
        for ch in ch_list:
            ch["group_title"] = canonical

    # Main live.m3u: catalog only (standard table matched)
    main_order = list(cat.iter_main_order())
    main_channels: list[dict] = []
    for key in main_order:
        if key == "overseas" and not main_include_overseas:
            continue
        if key in catalog:
            for ch in catalog[key]:
                main_channels.append({**ch, "group_title": cat.group_title(key)})

    generate_m3u(main_channels, os.path.join(output_abs, "live.m3u"), "Oasisic-IPTV")
    print(f"   live.m3u: {len(main_channels)} 条")

    # Category files (catalog only)
    for key, ch_list in catalog.items():
        if cat.is_radio(key):
            continue
        filename = cat.file_for(key)
        cat_channels = [{**ch, "group_title": cat.group_title(key)} for ch in ch_list]
        generate_m3u(cat_channels, os.path.join(output_abs, filename), f"Oasisic-IPTV - {cat.title_for(key)}")

    # Radio
    radio_key = cat.RADIO_KEY
    if radio_key in catalog:
        radio_list = [{**ch, "group_title": cat.group_title(radio_key)} for ch in catalog[radio_key]]
        generate_m3u(radio_list, os.path.join(output_abs, cat.file_for(radio_key)), "Oasisic-IPTV - 电台")
        print(f"   {cat.file_for(radio_key)}: {len(radio_list)} 条")

    print(f"   分类文件: {len([k for k in catalog if not cat.is_radio(k)])} 个类别")

    # ── live_more.m3u ──────────────────────────────────────────
    if write_more:
        more_channels = more[:more_max]
        if more_channels:
            # Normalize group_title for more
            for ch in more_channels:
                cat_key = ch.get("category", "other")
                ch["group_title"] = cat.group_title(cat_key)
            generate_m3u(more_channels, os.path.join(output_abs, "live_more.m3u"), "Oasisic-IPTV - More")
            print(f"   live_more.m3u: {len(more_channels)} 条")

    # ── live_verified.m3u (probe mode) ────────────────────────
    if _PROBE_ENABLED:
        verified_channels = [ch for ch in matched if ch.get("alive")]
        verified_dedup: list[dict] = []
        seen_urls: set[str] = set()
        for ch in verified_channels:
            url = ch.get("url", "")
            if url and url not in seen_urls:
                seen_urls.add(url)
                verified_dedup.append(ch)
        generate_m3u(verified_dedup, os.path.join(output_abs, "live_verified.m3u"), "Oasisic-IPTV - Verified")
        print(f"   live_verified.m3u: {len(verified_dedup)} 条")

    # ── 10. Write check_result.json ─────────────────────────────
    now = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=8)))
    probe_ratio = (probe_ok / (probe_ok + probe_fail) * 100) if (probe_ok + probe_fail) else 0.0
    check = {
        "schema_version": 1,
        "stage": "probe" if _PROBE_ENABLED else "collect",
        "generated_at": now.strftime("%Y-%m-%d %H:%M:%S"),
        "timezone": "Asia/Shanghai",
        "region": _PROBE_REGION,
        "total": total_selected,
        "catalog_count": catalog_total,
        "more_count": len(more),
        "ok": probe_ok,
        "fail": probe_fail,
        "ratio": round(probe_ratio, 1),
        "probe_enabled": _PROBE_ENABLED,
        "probe_concurrency": _PROBE_CONCURRENCY,
        "probe_timeout": _PROBE_TIMEOUT,
        "channels": [],
    }
    check_path = os.path.join(output_abs, "check_result.json")
    save_json(check_path, check)

    print()
    print("=" * 40)
    print(f"✅ 采集完成 (probe_enabled={_PROBE_ENABLED})")
    print(f"   总输出: {total_selected} 条")
    print(f"   目录: {catalog_total} 条 / 扩展: {len(more)} 条")
    print(f"   源成功率: {ok_count}/{total_enabled} ({success_rate:.0f}%)")
    if _PROBE_ENABLED:
        print(f"   测活: {probe_ok} 可用 / {probe_fail} 不可用 ({probe_ratio:.0f}%)")
    print(f"   check_result.json → {check_path}")
    print("=" * 40)


if __name__ == "__main__":
    main()