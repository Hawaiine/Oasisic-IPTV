#!/usr/bin/env python3
"""把 EPG 对齐结果写进 data/channels.json 的 `epg_id` 字段，并生成缺口清单。

- 幂等：重复运行不产生 diff；`--check` 只校验不写。
- 规则：`epg_id` 必须能在一个上游里命中且该 id 有 programme；否则写 null 并进缺口清单。
- 输出 M3U 时 `tvg-id = epg_id or tvg_id`（回退，保证零退化）。
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from lib.epg_map import (  # noqa: E402
    build_missing_report,
    fetch_upstreams,
    parse_channel_ids,
    parse_channels_with_names,
    parse_programme_counts,
)
from lib.io_util import load_json, load_yaml, project_root, save_text  # noqa: E402

FIELD_ORDER = ("standard_name", "display_name", "category", "tvg_id", "epg_id", "tvg_logo", "priority", "notes", "preferred_region")


def reorder(channel: dict) -> dict:
    out = {}
    for key in FIELD_ORDER:
        if key in channel:
            out[key] = channel[key]
    for key, value in channel.items():
        if key not in out:
            out[key] = value
    return out


async def collect_mapping(root: Path) -> tuple[dict, list[str], dict]:
    settings = load_yaml(root / "config" / "settings.yaml")
    urls = list(settings.get("epg_sources") or [])
    timeout = max(int(settings.get("request_timeout_sec") or 30), 120)
    ua = settings.get("user_agent") or "Oasisic-IPTV/1.0"
    channels = load_json(root / "data" / "channels.json")
    aliases = load_json(root / "data" / "aliases.json")

    results = await fetch_upstreams(urls, timeout=timeout, ua=ua)
    ids_all: set[str] = set()
    ids_with_prog: set[str] = set()
    name_index: dict[str, str] = {}
    stats: dict = {"sources": [], "coverage": 0.0}
    for url, text, err in results:
        if text is None:
            print(f"  ✗ {url} :: {err}")
            stats["sources"].append({"url": url, "ok": False, "error": err})
            continue
        progs = parse_programme_counts(text)
        gids = {k for k, v in progs.items() if v > 0}
        ids_all |= set(parse_channel_ids(text))
        ids_with_prog |= gids
        for cid, dn_list in parse_channels_with_names(text).items():
            if cid not in gids:
                continue
            for dn in dn_list:
                name_index.setdefault(dn, cid)
        print(f"  ✓ {url} :: 有节目单 id {len(gids)}")
        stats["sources"].append({"url": url, "ok": True, "ids_with_programme": len(gids)})

    mapping, missing = build_missing_report(
        channels,
        ids_all=ids_all,
        ids_with_programme=ids_with_prog,
        aliases=aliases,
        name_index=name_index,
    )
    matched = sum(1 for v in mapping.values() if v["epg_id"])
    stats["coverage"] = round(matched / len(channels), 4)
    stats["matched"] = matched
    stats["total"] = len(channels)
    return mapping, missing, stats


def main() -> None:
    parser = argparse.ArgumentParser(description="同步 EPG 对齐结果到 channels.json")
    parser.add_argument("--check", action="store_true", help="只校验，不写文件")
    args = parser.parse_args()

    root = project_root()
    settings = load_yaml(root / "config" / "settings.yaml")
    min_cov = float(settings.get("epg_min_coverage") or 0.6)

    print("== EPG 对齐同步 ==")
    mapping, missing, stats = asyncio.run(collect_mapping(root))
    print(f"覆盖率: {stats['matched']}/{stats['total']} = {stats['coverage']:.1%}（阈值 {min_cov:.0%}）")

    channels = load_json(root / "data" / "channels.json")
    changed = 0
    for ch in channels:
        want = mapping.get(ch["standard_name"], {}).get("epg_id")
        if ch.get("epg_id") != want:
            ch["epg_id"] = want
            changed += 1

    missing_lines = [
        "# Oasisic-IPTV EPG 缺口清单（自动生成，勿手改）",
        "# 格式：标准名 | 分类 | 原因（upstream-missing = 上游无此频道；upstream-no-programme = 有频道条目但无节目单）",
        "# 生成时间：" + __import__("datetime").datetime.now().astimezone().strftime("%Y-%m-%d %H:%M:%S"),
        f"# 覆盖率：{stats['matched']}/{stats['total']} = {stats['coverage']:.1%}",
        "",
    ] + missing + [""]

    if args.check:
        ok = stats["coverage"] >= min_cov
        print(f"{'✅' if ok else '❌'} --check：覆盖率 {stats['coverage']:.1%} 阈值 {min_cov:.0%}；缺口 {len(missing)} 条")
        if changed:
            print(f"⚠ channels.json 有 {changed} 条待写入（请运行无参数版本）")
        sys.exit(0 if ok else 1)

    channels = [reorder(c) for c in channels]
    save_text(
        root / "data" / "channels.json",
        json.dumps(channels, ensure_ascii=False, indent=4) + "\n",
    )
    save_text(root / "data" / "epg_missing.txt", "\n".join(missing_lines))
    print(f"✅ channels.json 更新 {changed} 条 epg_id；缺口清单 {len(missing)} 条 → data/epg_missing.txt")


if __name__ == "__main__":
    main()