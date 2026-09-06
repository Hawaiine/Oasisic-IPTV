#!/usr/bin/env python3
"""主入口：采集 → 解析 → 清洗 → 匹配 → 分类 → 选优 → 生成。只负责调度。"""

from __future__ import annotations

import argparse
import asyncio
import sys
from collections import defaultdict
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from lib.categories import RADIO_KEY, file_suffix, group_title, iter_main_order  # noqa: E402
from lib.classify import classify_entries  # noqa: E402
from lib.io_util import load_json, load_yaml, project_root, save_json, save_text  # noqa: E402
from lib.m3u import build_m3u, parse_playlist  # noqa: E402
from lib.match import ChannelMatcher, attach_match  # noqa: E402
from lib.select import order_for_output, select_best, split_catalog_more  # noqa: E402

CST = timezone(timedelta(hours=8))
# 台标走 jsDelivr，避免 live.fanmingming.com/.cn 在部分网络不可达
LOGO_BASE = "https://gcore.jsdelivr.net/gh/fanmingming/live@master/tv"


def now_cst() -> str:
    return datetime.now(CST).strftime("%Y-%m-%d %H:%M:%S")


def load_settings() -> dict[str, Any]:
    return load_yaml(project_root() / "config" / "settings.yaml")


def load_sources() -> list[dict[str, Any]]:
    data = load_yaml(project_root() / "config" / "sources.yaml")
    return list(data.get("sources") or [])


def _logo_url(tvg_id: str) -> str:
    return f"{LOGO_BASE}/{tvg_id}.png"


def fill_logo(entry: dict[str, Any]) -> dict[str, Any]:
    """缺 logo 时补 jsDelivr；已有 fanmingming.com/.cn 的也改成镜像。"""
    tvg_id = entry.get("tvg_id") or ""
    logo = entry.get("tvg_logo") or ""
    if "live.fanmingming." in logo and tvg_id:
        entry = dict(entry)
        entry["tvg_logo"] = _logo_url(tvg_id)
        return entry
    if logo:
        return entry
    if tvg_id:
        entry = dict(entry)
        entry["tvg_logo"] = _logo_url(tvg_id)
    return entry


async def fetch_one(
    session: Any,
    source: dict[str, Any],
    timeout: int,
    user_agent: str,
) -> dict[str, Any]:
    url = source.get("url") or ""
    key = source.get("key") or source.get("name") or url
    result: dict[str, Any] = {
        "key": key,
        "source": source,
        "ok": False,
        "status": 0,
        "error": "",
        "text": "",
        "count": 0,
    }
    if not source.get("enabled", True):
        result["error"] = "disabled"
        return result
    try:
        import aiohttp

        async with session.get(
            url,
            timeout=aiohttp.ClientTimeout(total=timeout),
            headers={"User-Agent": user_agent},
        ) as resp:
            result["status"] = resp.status
            if resp.status != 200:
                result["error"] = f"HTTP {resp.status}"
                return result
            text = await resp.text(errors="replace")
            result["text"] = text
            result["ok"] = True
            return result
    except Exception as exc:  # noqa: BLE001
        result["error"] = f"{type(exc).__name__}: {exc}"
        return result


async def fetch_all(
    sources: list[dict[str, Any]],
    settings: dict[str, Any],
) -> list[dict[str, Any]]:
    import aiohttp

    timeout = int(settings.get("request_timeout_sec") or 30)
    ua = settings.get("user_agent") or "Oasisic-IPTV/1.0"
    connector = aiohttp.TCPConnector(limit=8, ssl=False)
    async with aiohttp.ClientSession(connector=connector) as session:
        tasks = [fetch_one(session, s, timeout, ua) for s in sources]
        return await asyncio.gather(*tasks)


def parse_fetched(fetched: list[dict[str, Any]]) -> list[dict[str, Any]]:
    entries: list[dict[str, Any]] = []
    for item in fetched:
        src = item["source"]
        if not item["ok"]:
            print(f"  ✗ {item['key']}: {item['error']}")
            continue
        text = item["text"]
        stype = (src.get("type") or "m3u").lower()
        parsed = parse_playlist(text, stype)
        item["count"] = len(parsed)
        if not parsed:
            item["ok"] = False
            item["error"] = "empty or unparseable"
            print(f"  ✗ {item['key']}: 可访问但未解析到频道")
            continue
        print(f"  ✓ {item['key']}: {len(parsed)} 条")
        for e in parsed:
            rec = dict(e)
            rec["source_key"] = item["key"]
            rec["source_region"] = src.get("region") or "cn"
            rec["source_priority"] = int(src.get("priority") or 50)
            rec["source_core"] = bool(src.get("core", False))
            entries.append(rec)
    return entries


def record_source_stats(
    fetched: list[dict[str, Any]],
    settings: dict[str, Any],
) -> None:
    """写入 data/source_stats.json，并按连续失败天数自动禁用非核心源。"""
    path = project_root() / "data" / "source_stats.json"
    today = datetime.now(CST).strftime("%Y-%m-%d")
    stats: dict[str, Any] = {"schema_version": 1, "sources": {}}
    if path.exists():
        try:
            stats = load_json(path)
        except Exception:  # noqa: BLE001
            stats = {"schema_version": 1, "sources": {}}
    sources_map: dict[str, Any] = stats.setdefault("sources", {})
    fail_days = int(settings.get("auto_disable_fail_days") or 3)

    yaml_path = project_root() / "config" / "sources.yaml"
    raw_yaml = yaml_path.read_text(encoding="utf-8")
    changed = False

    for item in fetched:
        key = item["key"]
        rec = sources_map.setdefault(
            key,
            {"ok": 0, "fail": 0, "consecutive_fail": 0, "last_ok": "", "last_fail": "", "last_count": 0},
        )
        if item["ok"]:
            rec["ok"] = int(rec.get("ok") or 0) + 1
            rec["consecutive_fail"] = 0
            rec["last_ok"] = today
            rec["last_count"] = item.get("count") or 0
            rec["last_error"] = ""
        else:
            if item.get("error") == "disabled":
                continue
            rec["fail"] = int(rec.get("fail") or 0) + 1
            rec["consecutive_fail"] = int(rec.get("consecutive_fail") or 0) + 1
            rec["last_fail"] = today
            rec["last_error"] = item.get("error") or ""
            src = item["source"]
            if (
                rec["consecutive_fail"] >= fail_days
                and not src.get("core")
                and src.get("enabled", True)
            ):
                print(
                    f"  ⚠ 源 {key} 连续 {rec['consecutive_fail']} 天失败，自动禁用"
                )
                # 仅改 enabled 行，避免重写整个 YAML 打乱注释
                # 通过 key 定位块后替换该源的 enabled
                changed = _disable_source_in_yaml(raw_yaml, key)
                if changed:
                    raw_yaml = yaml_path.read_text(encoding="utf-8")
            elif src.get("core") and rec["consecutive_fail"] >= fail_days:
                print(f"  ⚠ 核心源 {key} 连续失败 {rec['consecutive_fail']} 天（仅告警，不禁用）")

    stats["updated_at"] = now_cst()
    known = {item["key"] for item in fetched}
    stats["sources"] = {k: v for k, v in sources_map.items() if k in known}
    save_json(path, stats)


def _disable_source_in_yaml(text: str, key: str) -> bool:
    """在 sources.yaml 中把指定 key 的 enabled 改为 false。"""
    path = project_root() / "config" / "sources.yaml"
    lines = path.read_text(encoding="utf-8").splitlines(keepends=True)
    in_block = False
    replaced = False
    for i, line in enumerate(lines):
        if line.strip().startswith("- key:") or line.strip().startswith("- name:"):
            in_block = key in line
        if in_block and "enabled:" in line:
            lines[i] = line.replace("enabled: true", "enabled: false").replace(
                "enabled: True", "enabled: false"
            )
            replaced = True
            in_block = False
    if replaced:
        path.write_text("".join(lines), encoding="utf-8")
    return replaced


def write_outputs(
    catalog: list[dict[str, Any]],
    more: list[dict[str, Any]],
    radio: list[dict[str, Any]],
    backup: list[dict[str, Any]],
    settings: dict[str, Any],
) -> dict[str, int]:
    out_dir = project_root() / (settings.get("output_dir") or "output/")
    out_dir.mkdir(parents=True, exist_ok=True)

    catalog = [fill_logo(e) for e in order_for_output(catalog)]
    more_ordered = [fill_logo(e) for e in order_for_output(more)]
    backup_ordered = [fill_logo(e) for e in order_for_output(backup)]
    radio_ordered = [fill_logo(e) for e in radio]
    for e in radio_ordered:
        e["group_title"] = group_title(RADIO_KEY)

    url_tvg = settings.get("url_tvg") or "https://live.fanmingming.com/e.xml"
    save_text(
        out_dir / "live.m3u",
        build_m3u(catalog, playlist_title="Oasisic-IPTV 精选", url_tvg=url_tvg),
    )
    if settings.get("write_live_more", True):
        save_text(
            out_dir / "live_more.m3u",
            build_m3u(more_ordered, playlist_title="Oasisic-IPTV 扩展", url_tvg=url_tvg),
        )
    if settings.get("write_live_backup", True):
        save_text(
            out_dir / "live_backup.m3u",
            build_m3u(backup_ordered, playlist_title="Oasisic-IPTV 备份", url_tvg=url_tvg),
        )

    by_cat: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for e in catalog:
        by_cat[e.get("category") or "other"].append(e)
    # 分类文件与主列表同口径（仅 catalog）
    for cat in iter_main_order():
        suffix = file_suffix(cat)
        items = by_cat.get(cat) or []
        title = group_title(cat)
        save_text(
            out_dir / f"live_{suffix}.m3u",
            build_m3u(items, playlist_title=title, url_tvg=url_tvg),
        )

    save_text(
        out_dir / "live_radio.m3u",
        build_m3u(radio_ordered, playlist_title="电台", url_tvg=url_tvg),
    )
    return {
        "catalog": len(catalog),
        "more": len(more_ordered),
        "radio": len(radio_ordered),
        "backup": len(backup_ordered),
    }


def write_check_result(
    counts: dict[str, int],
    fetched: list[dict[str, Any]],
    settings: dict[str, Any],
) -> None:
    enabled = [f for f in fetched if f["source"].get("enabled", True)]
    ok_n = sum(1 for f in enabled if f["ok"])
    fail_n = len(enabled) - ok_n
    total = ok_n + fail_n
    ratio = (ok_n / total) if total else 0.0
    payload = {
        "schema_version": 1,
        "stage": "collect",
        "generated_at": now_cst(),
        "timezone": "Asia/Shanghai",
        "total": counts["catalog"] + counts["more"] + counts["radio"],
        "catalog": counts["catalog"],
        "more": counts["more"],
        "radio": counts["radio"],
        "backup": counts.get("backup") or 0,
        "ok": ok_n,
        "fail": fail_n,
        "ratio": round(ratio, 4),
        "sources": [
            {
                "key": f["key"],
                "ok": f["ok"],
                "status": f.get("status") or 0,
                "count": f.get("count") or 0,
                "error": f.get("error") or "",
            }
            for f in fetched
        ],
        "channels": [],
    }
    out_dir = project_root() / (settings.get("output_dir") or "output/")
    save_json(out_dir / "check_result.json", payload)


def enforce_strict(fetched: list[dict[str, Any]], settings: dict[str, Any]) -> None:
    enabled = [f for f in fetched if f["source"].get("enabled", True)]
    if not enabled:
        print("❌ 没有任何启用源")
        sys.exit(1)
    ok_n = sum(1 for f in enabled if f["ok"])
    ratio = ok_n / len(enabled)
    threshold = float(settings.get("strict_sources_ratio") or 0.7)
    core = [f for f in enabled if f["source"].get("core")]
    core_ok = sum(1 for f in core if f["ok"]) if core else -1
    print(f"源成功率: {ok_n}/{len(enabled)} = {ratio:.0%}")
    if core and core_ok == 0:
        print("❌ 严格模式：核心源全部失败")
        sys.exit(1)
    if ratio < threshold:
        print(f"❌ 严格模式：成功率 {ratio:.0%} < {threshold:.0%}")
        sys.exit(1)


def run() -> int:
    settings = load_settings()
    sources = load_sources()
    root = project_root()
    channels = load_json(root / "data" / "channels.json")
    aliases = load_json(root / "data" / "aliases.json")
    matcher = ChannelMatcher(channels, aliases)

    print("== Oasisic-IPTV collect ==")
    print(f"源数量: {len(sources)}（启用 {sum(1 for s in sources if s.get('enabled', True))}）")
    fetched = asyncio.run(fetch_all(sources, settings))
    parsed = parse_fetched(fetched)
    print(f"解析合计: {len(parsed)}")

    record_source_stats(fetched, settings)
    enforce_strict(fetched, settings)

    matched = attach_match(parsed, matcher)
    classified = classify_entries(matched)
    max_keep = int(settings.get("max_keep_per_channel") or 1)
    selected = select_best(classified, max_keep=max_keep)
    include_ov = bool(settings.get("main_include_overseas", False))
    catalog, more, radio = split_catalog_more(
        selected,
        more_max_channels=int(settings.get("more_max_channels") or 3000),
        main_include_overseas=include_ov,
    )
    backup: list[dict[str, Any]] = []
    if settings.get("write_live_backup", True):
        backup_keep = int(settings.get("backup_max_keep") or 3)
        backup_pool = [
            e
            for e in classified
            if e.get("matched")
            and e.get("category") != RADIO_KEY
            and (include_ov or e.get("category") != "overseas")
        ]
        backup = select_best(backup_pool, max_keep=backup_keep)
    counts = write_outputs(catalog, more, radio, backup, settings)
    write_check_result(counts, fetched, settings)
    print(
        f"✅ catalog={counts['catalog']} / more={counts['more']} / "
        f"backup={counts.get('backup', 0)} / radio={counts['radio']}"
    )
    return 0


def main() -> None:
    parser = argparse.ArgumentParser(description="Oasisic-IPTV 采集（不检测直播流）")
    parser.parse_args()
    try:
        raise SystemExit(run())
    except KeyboardInterrupt:
        print("中断")
        raise SystemExit(130)


if __name__ == "__main__":
    main()
