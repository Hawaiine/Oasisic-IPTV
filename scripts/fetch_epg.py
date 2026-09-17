#!/usr/bin/env python3
"""拉取 EPG（多源真合并）、按标准表 epg_id/tvg_id 裁剪、programme 去重，写出 guide.xml。"""

from __future__ import annotations

import argparse
import asyncio
import gzip
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from lib.epg_map import fetch_upstreams, load_epg_ids  # noqa: E402
from lib.io_util import load_json, load_yaml, project_root, save_text  # noqa: E402


def load_allowed_ids() -> set[str]:
    """裁剪白名单：epg_id 优先、tvg_id 回退（两口径都收，保证零退化）。"""
    channels = load_json(project_root() / "data" / "channels.json")
    return load_epg_ids(channels)


def merge_and_clip(
    blobs: list[tuple[str, str]],
    allowed: set[str],
) -> tuple[ET.Element, dict[str, int], dict[str, dict[str, int]]]:
    """多源合并：channel / programme 先到先得；只保留 allowed 中的 id。

    返回 (root, 汇总统计, 每源贡献)。
    """
    root = ET.Element("tv")
    seen_ch: set[str] = set()
    seen_prog: set[tuple[str, str, str]] = set()
    stats = {
        "channel_kept": 0,
        "channel_skipped": 0,
        "programme_kept": 0,
        "programme_dup": 0,
        "programme_skipped": 0,
        "parse_fail": 0,
    }
    per_source: dict[str, dict[str, int]] = {}
    for url, blob in blobs:
        src = {"channel_kept": 0, "programme_kept": 0}
        try:
            tree = ET.fromstring(blob)
        except ET.ParseError:
            stats["parse_fail"] += 1
            per_source[url] = {"channel_kept": 0, "programme_kept": 0, "parse_fail": 1}
            continue
        for ch in tree.findall("channel"):
            cid = (ch.get("id") or "").strip()
            if not cid:
                continue
            if allowed and cid not in allowed:
                stats["channel_skipped"] += 1
                continue
            if cid in seen_ch:
                continue
            seen_ch.add(cid)
            root.append(ch)
            stats["channel_kept"] += 1
            src["channel_kept"] += 1
        for prog in tree.findall("programme"):
            cid = (prog.get("channel") or "").strip()
            if allowed and cid not in allowed:
                stats["programme_skipped"] += 1
                continue
            key = (cid, prog.get("start") or "", prog.get("stop") or "")
            if key in seen_prog:
                stats["programme_dup"] += 1
                continue
            seen_prog.add(key)
            root.append(prog)
            stats["programme_kept"] += 1
            src["programme_kept"] += 1
        per_source[url] = src
    return root, stats, per_source


def xml_bytes(root: ET.Element) -> bytes:
    body = ET.tostring(root, encoding="unicode")
    return ('<?xml version="1.0" encoding="UTF-8"?>\n' + body).encode("utf-8")


def write_outputs(root: ET.Element) -> tuple[Path, Path]:
    out_dir = project_root() / "output"
    out_dir.mkdir(parents=True, exist_ok=True)
    xml_path = out_dir / "guide.xml"
    gz_path = out_dir / "guide.xml.gz"
    data = xml_bytes(root)
    save_text(xml_path, data.decode("utf-8"))
    with gzip.open(gz_path, "wb") as f:
        f.write(data)
    return xml_path, gz_path


def main() -> None:
    parser = argparse.ArgumentParser(description="拉取并裁剪 EPG（多源真合并，写入 git 的是裁剪版）")
    parser.parse_args()
    settings = load_yaml(project_root() / "config" / "settings.yaml")
    urls = list(settings.get("epg_sources") or [])
    if not urls:
        print("❌ settings.yaml 未配置 epg_sources")
        sys.exit(1)
    timeout = max(int(settings.get("request_timeout_sec") or 30), 120)
    ua = settings.get("user_agent") or "Oasisic-IPTV/1.0"
    allowed = load_allowed_ids()
    print(f"裁剪白名单（epg_id ∪ tvg_id）: {len(allowed)} 个 id")

    results = asyncio.run(fetch_upstreams(urls, timeout=timeout, ua=ua))
    blobs: list[tuple[str, str]] = []
    for url, text, err in results:
        if text is None:
            print(f"  ✗ {url}: {err}")
            continue
        print(f"  ✓ {url} ({len(text)//1024} KB)")
        blobs.append((url, text))
    if not blobs:
        print("❌ 没有成功的 EPG 源")
        sys.exit(1)

    root, stats, per_source = merge_and_clip(blobs, allowed)
    for url, src in per_source.items():
        extra = f" parse_fail={src['parse_fail']}" if src.get("parse_fail") else ""
        print(f"    {url} 贡献 channel={src['channel_kept']} programme={src['programme_kept']}{extra}")

    xml_path, gz_path = write_outputs(root)
    kept_ids = {ch.get("id") for ch in root.findall("channel")}
    print(
        f"channel kept={stats['channel_kept']} skipped={stats['channel_skipped']} | "
        f"programme kept={stats['programme_kept']} dup={stats['programme_dup']} "
        f"skipped={stats['programme_skipped']} parse_fail={stats['parse_fail']}"
    )
    print(f"✅ 裁剪版 {xml_path} ({xml_path.stat().st_size} bytes)")
    print(f"✅ gzip {gz_path} ({gz_path.stat().st_size} bytes)")

    channels = load_json(project_root() / "data" / "channels.json")
    total = len(channels)
    covered = sum(1 for ch in channels if (ch.get("epg_id") or ch.get("tvg_id")) in kept_ids)
    print(f"覆盖率: {covered}/{total} = {covered/total:.1%}")
    missing = sorted(
        ch["standard_name"]
        for ch in channels
        if (ch.get("epg_id") or ch.get("tvg_id")) not in kept_ids
    )
    if missing:
        print(f"⚠ 未覆盖 {len(missing)} 个（清单见 data/epg_missing.txt）: {missing[:10]}")


if __name__ == "__main__":
    main()