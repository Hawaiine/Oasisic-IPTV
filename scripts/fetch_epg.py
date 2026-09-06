#!/usr/bin/env python3
"""拉取 EPG、按标准表 tvg_id 裁剪、programme 去重，写出裁剪版 guide.xml。"""

from __future__ import annotations

import argparse
import asyncio
import gzip
import sys
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from lib.io_util import load_json, load_yaml, project_root, save_text  # noqa: E402


def load_allowed_tvg_ids() -> set[str]:
    channels = load_json(project_root() / "data" / "channels.json")
    return {str(ch.get("tvg_id") or "").strip() for ch in channels if ch.get("tvg_id")}


async def fetch(url: str, timeout: int, ua: str) -> str:
    import aiohttp

    connector = aiohttp.TCPConnector(ssl=False)
    async with aiohttp.ClientSession(connector=connector) as session:
        async with session.get(
            url,
            timeout=aiohttp.ClientTimeout(total=timeout),
            headers={"User-Agent": ua, "Accept-Encoding": "gzip, deflate"},
        ) as resp:
            resp.raise_for_status()
            raw = await resp.read()
            if url.endswith(".gz") or raw[:2] == b"\x1f\x8b":
                return gzip.decompress(raw).decode("utf-8", errors="replace")
            return raw.decode("utf-8", errors="replace")


def merge_and_clip(
    blobs: list[str],
    allowed: set[str],
) -> tuple[ET.Element, dict[str, int]]:
    """多源合并：channel / programme 均先到先得；只保留 allowed 中的 tvg_id。"""
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
    for blob in blobs:
        try:
            tree = ET.fromstring(blob)
        except ET.ParseError:
            stats["parse_fail"] += 1
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
    return root, stats


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
    parser = argparse.ArgumentParser(description="拉取并裁剪 EPG（写入 git 的是裁剪版）")
    parser.parse_args()
    settings = load_yaml(project_root() / "config" / "settings.yaml")
    urls = list(settings.get("epg_sources") or [])
    if not urls:
        print("settings.yaml 未配置 epg_sources")
        sys.exit(1)
    timeout = max(int(settings.get("request_timeout_sec") or 30), 120)
    ua = settings.get("user_agent") or "Oasisic-IPTV/1.0"
    allowed = load_allowed_tvg_ids()
    print(f"标准表 tvg_id: {len(allowed)}")

    async def _run() -> list[str]:
        out: list[str] = []
        for url in urls:
            try:
                text = await fetch(url, timeout, ua)
                out.append(text)
                print(f"  ✓ {url} ({len(text)} chars)")
                break  # 先到先得；后续条目仅作回落
            except Exception as exc:  # noqa: BLE001
                print(f"  ✗ {url}: {exc}")
        return out

    blobs = asyncio.run(_run())
    if not blobs:
        print("❌ 没有成功的 EPG 源")
        sys.exit(1)
    root, stats = merge_and_clip(blobs, allowed)
    xml_path, gz_path = write_outputs(root)
    print(
        f"channel kept={stats['channel_kept']} skipped={stats['channel_skipped']} | "
        f"programme kept={stats['programme_kept']} dup={stats['programme_dup']} "
        f"skipped={stats['programme_skipped']} parse_fail={stats['parse_fail']}"
    )
    print(f"✅ 裁剪版 {xml_path} ({xml_path.stat().st_size} bytes)")
    print(f"✅ gzip {gz_path} ({gz_path.stat().st_size} bytes)")
    missing = sorted(allowed - {ch.get("id") for ch in root.findall("channel")})
    if missing:
        print(f"⚠ 标准表 {len(missing)} 个 tvg_id 未出现在 EPG: {missing[:12]}")


if __name__ == "__main__":
    main()
