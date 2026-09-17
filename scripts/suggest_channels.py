#!/usr/bin/env python3
"""标准表扩容助手：从 live_more 长尾里挑出「有上游 EPG」的频道，生成入表候选。

只读候选 → `data/channels_candidates.json`；`--apply` 才写入 channels.json（幂等，已存在的不重复加）。

入表判据（宁缺毋滥）：
1. 名称不在黑名单、不在标准表/别名里；
2. 归一化后能在 EPG 上游命中有节目单的 id（入表即自带节目单）；
3. 分类可判定（cctv/weishi/local/gangtai/sports 之一，other 不入选）。
"""

from __future__ import annotations

import argparse
import asyncio
import json
import re
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from lib.classify import classify_name  # noqa: E402
from lib.epg_map import (  # noqa: E402
    fetch_upstreams,
    parse_channels_with_names,
    parse_programme_counts,
)
from lib.exclude import is_excluded, load_patterns  # noqa: E402
from lib.io_util import load_json, load_yaml, project_root, save_text  # noqa: E402
from lib.m3u import parse_m3u  # noqa: E402

_QUALITY_RE = re.compile(r"[\s\-—_]*(1080[pP]|720[pP]|4K|8K|高清|超清|标清|蓝光|HD|SD)\s*$")
_MARK_RE = re.compile(r"^[\s“”\"'\[\]【】()（）\-—_]+|[\s“”\"'\[\]【】()（）\-—_]+$")
_BRACKET_RE = re.compile(r"[（(\[][^）)\]]*[）)\]]\s*$")


def normalize(name: str) -> str:
    n = (name or "").strip()
    n = _BRACKET_RE.sub("", n)
    n = _QUALITY_RE.sub("", n)
    n = re.sub(r"^(“|《|\")?(HK|CN|TW|US|RU|中|港|台)(”|》|\")?", "", n).strip()
    n = _MARK_RE.sub("", n)
    n = re.sub(r"\s+", " ", n)
    return n.strip()


def ascii_safe(text: str) -> bool:
    return bool(text) and text.isascii() and all(c.isalnum() or c in "+-_" for c in text)


async def build_candidates() -> tuple[list[dict[str, Any]], dict[str, Any]]:
    root = project_root()
    settings = load_yaml(root / "config" / "settings.yaml")
    channels = load_json(root / "data" / "channels.json")
    aliases = load_json(root / "data" / "aliases.json")

    table_names = {c["standard_name"] for c in channels} | {c["display_name"] for c in channels}
    alias_all = {a for v in aliases.values() for a in v}
    patterns = load_patterns(load_yaml(root / "config" / "exclude.yaml") if (root / "config" / "exclude.yaml").exists() else None)

    results = await fetch_upstreams(
        list(settings.get("epg_sources") or []),
        timeout=max(int(settings.get("request_timeout_sec") or 30), 120),
        ua=settings.get("user_agent") or "Oasisic-IPTV/1.0",
    )
    ids_with_prog: set[str] = set()
    name_index: dict[str, str] = {}
    for url, text, err in results:
        if text is None:
            print(f"  ✗ {url}: {err}")
            continue
        progs = parse_programme_counts(text)
        gids = {k for k, v in progs.items() if v > 0}
        ids_with_prog |= gids
        for cid, dns in parse_channels_with_names(text).items():
            if cid in gids:
                for dn in dns:
                    name_index.setdefault(dn, cid)

    more = parse_m3u((root / "output" / "live_more.m3u").read_text(encoding="utf-8"))
    raw_names = [e["name"] for e in more]

    variants: dict[str, set[str]] = {}
    proposals: dict[str, dict[str, Any]] = {}
    skipped = {"excluded": 0, "known": 0, "no_epg": 0, "other_cat": 0, "bad_name": 0}

    for raw in raw_names:
        if is_excluded(raw, patterns):
            skipped["excluded"] += 1
            continue
        name = normalize(raw)
        if not name or len(name) > 24:
            skipped["bad_name"] += 1
            continue
        if name in table_names or name in alias_all:
            skipped["known"] += 1
            continue
        cat = classify_name(name, "cn")
        if cat == "other":
            skipped["other_cat"] += 1
            continue
        epg_id = name if name in ids_with_prog else name_index.get(name)
        if not epg_id:
            skipped["no_epg"] += 1
            continue
        rec = proposals.setdefault(
            name,
            {
                "standard_name": name,
                "display_name": name,
                "category": cat,
                "epg_id": epg_id,
                "tvg_id": epg_id if ascii_safe(epg_id) else "",
                "tvg_logo": "",
                "source_names": [],
            },
        )
        variants.setdefault(name, set()).add(raw)
        if raw not in rec["source_names"]:
            rec["source_names"].append(raw)

    out = sorted(proposals.values(), key=lambda r: (r["category"], r["standard_name"]))
    stats = {
        "live_more_total": len(raw_names),
        "unique_candidates": len(out),
        "skipped": skipped,
        "by_category": {},
    }
    for rec in out:
        stats["by_category"][rec["category"]] = stats["by_category"].get(rec["category"], 0) + 1
    for rec in out:
        rec["aliases"] = sorted(variants.get(rec["standard_name"], set()) - {rec["standard_name"]})
    return out, stats


def apply_candidates(candidates: list[dict[str, Any]]) -> tuple[int, int]:
    root = project_root()
    channels: list[dict[str, Any]] = load_json(root / "data" / "channels.json")
    aliases: dict[str, list[str]] = load_json(root / "data" / "aliases.json")
    existing = {c["standard_name"] for c in channels}
    added = 0
    alias_added = 0
    for rec in candidates:
        name = rec["standard_name"]
        if name in existing:
            continue
        channels.append(
            {
                "standard_name": name,
                "display_name": name,
                "category": rec["category"],
                "tvg_id": rec["tvg_id"],
                "epg_id": rec["epg_id"],
                "tvg_logo": rec["tvg_logo"],
                "priority": 60,
                "notes": "long-tail",
            }
        )
        existing.add(name)
        added += 1
        als = [a for a in rec.get("aliases", []) if a]
        if als:
            cur = list(aliases.get(name) or [])
            for a in als:
                if a not in cur and a not in alias_all_flat(aliases):
                    cur.append(a)
                    alias_added += 1
            if cur:
                aliases[name] = cur
    save_text(root / "data" / "channels.json", json.dumps(channels, ensure_ascii=False, indent=4) + "\n")
    save_text(root / "data" / "aliases.json", json.dumps(aliases, ensure_ascii=False, indent=4) + "\n")
    return added, alias_added


def alias_all_flat(aliases: dict[str, list[str]]) -> set[str]:
    return {a for v in aliases.values() for a in v}


def main() -> None:
    parser = argparse.ArgumentParser(description="标准表扩容候选（默认只读）")
    parser.add_argument("--apply", action="store_true", help="把候选写入 channels.json / aliases.json")
    parser.add_argument("--limit", type=int, default=0, help="只看前 N 条候选")
    args = parser.parse_args()
    root = project_root()

    candidates, stats = asyncio.run(build_candidates())
    if args.limit:
        candidates = candidates[: args.limit]
    out = root / "data" / "channels_candidates.json"
    save_text(out, json.dumps(candidates, ensure_ascii=False, indent=2) + "\n")
    print("\n== 扩容候选 ==")
    print(f"live_more 名字 {stats['live_more_total']} | 候选 {stats['unique_candidates']} | 分布 {stats['by_category']}")
    print(f"跳过：{stats['skipped']}")
    print(f"✅ 候选写入 {out.relative_to(root)}")
    for rec in candidates[:30]:
        print(f"   [{rec['category']:8s}] {rec['standard_name']:20s} epg_id={rec['epg_id']} tvg_id={rec['tvg_id'] or '-'}")

    if args.apply:
        added, alias_added = apply_candidates(candidates)
        print(f"\n✅ 入表 {added} 个新频道，新增别名 {alias_added} 条")


if __name__ == "__main__":
    main()