#!/usr/bin/env python3
"""EPG 上游盘点：拉取全部 epg_sources，统计 id 体系与对本仓库标准表的命中情况。

输出 `output/epg_inventory.json`（机器用）与终端摘要（人看）。
只读，不改任何仓库数据。
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from lib.epg_map import (  # noqa: E402
    build_missing_report,
    fetch_upstreams,
    parse_channel_ids,
    parse_channels_with_names,
    parse_programme_counts,
)
from lib.io_util import load_json, load_yaml, project_root, save_json  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description="EPG 上游盘点（多源，不 break）")
    parser.add_argument("--json-out", default="output/epg_inventory.json")
    parser.parse_args()

    root = project_root()
    settings = load_yaml(root / "config" / "settings.yaml")
    urls = list(settings.get("epg_sources") or [])
    if not urls:
        print("❌ settings.yaml 未配置 epg_sources")
        sys.exit(1)
    timeout = max(int(settings.get("request_timeout_sec") or 30), 120)
    ua = settings.get("user_agent") or "Oasisic-IPTV/1.0"

    channels = load_json(root / "data" / "channels.json")
    aliases = load_json(root / "data" / "aliases.json")
    print(f"标准表: {len(channels)} 实体 | 上游: {len(urls)} 个")

    results = asyncio.run(fetch_upstreams(urls, timeout=timeout, ua=ua))

    ids_all: set[str] = set()
    ids_with_prog: set[str] = set()
    name_index: dict[str, str] = {}
    per_source: list[dict[str, Any]] = []
    for url, text, err in results:
        if text is None:
            print(f"  ✗ {url} :: {err}")
            per_source.append({"url": url, "ok": False, "error": err})
            continue
        ids = parse_channel_ids(text)
        progs = parse_programme_counts(text)
        gids = {k for k, v in progs.items() if v > 0}
        names = parse_channels_with_names(text)
        # 名字直配：按 epg_sources 顺序先到先得（先出现的源优先）
        for cid, dn_list in names.items():
            if cid not in gids:
                continue
            for dn in dn_list:
                name_index.setdefault(dn, cid)
        ids_all |= set(ids)
        ids_with_prog |= gids
        entry = {
            "url": url,
            "ok": True,
            "channels": len(set(ids)),
            "programmes": sum(progs.values()),
            "ids_with_programme": len(gids),
            "named": len(names),
            "id_sample": sorted(set(ids))[:15],
            "kb": len(text) // 1024,
        }
        per_source.append(entry)
        print(
            f"  ✓ {url}\n      频道 {entry['channels']} | programme {entry['programmes']} "
            f"| 有节目单的 id {len(gids)} | 带 display-name {entry['named']} | {entry['kb']} KB"
        )

    mapping, missing = build_missing_report(
        channels,
        ids_all=ids_all,
        ids_with_programme=ids_with_prog,
        aliases=aliases,
        name_index=name_index,
    )
    hit = {k for k, v in mapping.items() if v["epg_id"]}
    by_cat: dict[str, list[int]] = {}
    for ch in channels:
        got = 1 if mapping[ch["standard_name"]]["epg_id"] else 0
        t, g = by_cat.get(ch.get("category") or "other", [0, 0])
        by_cat[ch.get("category") or "other"] = [t + 1, g + got]

    print(f"\n合并后有节目单的 id: {len(ids_with_prog)} | 上游频道 id 合计: {len(ids_all)}")
    print(f"标准表可对齐: {len(hit)}/{len(channels)} = {len(hit)/len(channels):.1%}")
    for cat in sorted(by_cat):
        t, g = by_cat[cat]
        print(f"  {cat:9s} {g}/{t}")

    payload = {
        "schema_version": 1,
        "generated_at": datetime.now().astimezone().strftime("%Y-%m-%d %H:%M:%S"),
        "sources": per_source,
        "totals": {
            "ids_all": len(ids_all),
            "ids_with_programme": len(ids_with_prog),
            "channels": len(channels),
            "matched": len(hit),
            "coverage": round(len(hit) / len(channels), 4),
        },
        "by_category": {k: {"total": v[0], "matched": v[1]} for k, v in sorted(by_cat.items())},
        "missing": missing,
    }
    out = root / "output" / "epg_inventory.json"
    save_json(out, payload)
    print(f"\n✅ 写入 {out.relative_to(root)}")


if __name__ == "__main__":
    main()