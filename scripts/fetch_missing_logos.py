#!/usr/bin/env python3
"""为缺失台标的频道抓取台标（上游镜像 → 校验 PNG → 落地 logo/ → 回填 tvg_logo）。

安全规则：
- 只接受真 PNG（魔数校验）且 ≤ 200 KB；
- 文件名 = `tvg_id or epg_id`（与 M3U 的 logo 规则一致，避免 404）；
- 抓不到就写进 data/logo_missing.txt，**绝不**写外部 URL 到 tvg_logo。
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path
from typing import Any
from urllib.parse import quote

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from lib.io_util import load_json, project_root, save_text  # noqa: E402

PNG_MAGIC = b"\x89PNG\r\n\x1a\n"
MAX_BYTES = 200 * 1024
MIRRORS = (
    "https://gcore.jsdelivr.net/gh/fanmingming/live@master/tv/{q}.png",
    "https://raw.githubusercontent.com/fanmingming/live/main/tv/{q}.png",
    "https://live.fanmingming.cn/tv/{q}.png",
)


def name_variants(display: str, tvg_id: str) -> list[str]:
    out: list[str] = []
    for base in (display, tvg_id):
        base = (base or "").strip()
        if not base:
            continue
        out.append(base)
        if base.startswith("CCTV-"):
            out.append(base[5:])
            out.append("CCTV" + base[5:])
        if base.startswith("CCTV") and not base.startswith("CCTV-"):
            out.append(base.replace("CCTV", "CCTV-", 1))
        out.append(base.replace(" ", ""))
    seen: set[str] = set()
    ordered: list[str] = []
    for v in out:
        if v and v not in seen:
            seen.add(v)
            ordered.append(v)
    return ordered


async def fetch(url: str, timeout: float = 10) -> bytes | None:
    import aiohttp

    try:
        connector = aiohttp.TCPConnector(ssl=False)
        async with aiohttp.ClientSession(connector=connector) as s:
            async with s.get(url, timeout=aiohttp.ClientTimeout(total=timeout),
                             headers={"User-Agent": "Mozilla/5.0"}) as r:
                if r.status != 200:
                    return None
                data = await r.read()
                if len(data) > MAX_BYTES or not data.startswith(PNG_MAGIC):
                    return None
                return data
    except Exception:  # noqa: BLE001
        return None


async def grab(channel: dict[str, Any]) -> tuple[str, bytes | None]:
    key = (channel.get("tvg_id") or channel.get("epg_id") or "").strip()
    if not key:
        return "", None
    for name in name_variants(channel.get("display_name") or "", channel.get("tvg_id") or ""):
        for tpl in MIRRORS:
            data = await fetch(tpl.format(q=quote(name)))
            if data:
                return key, data
    return key, None


async def main() -> None:
    parser = argparse.ArgumentParser(description="抓取缺失台标")
    parser.add_argument("--limit", type=int, default=0, help="只处理前 N 个（调试）")
    parser.add_argument("--concurrency", type=int, default=8)
    args = parser.parse_args()

    root = project_root()
    channels: list[dict[str, Any]] = load_json(root / "data" / "channels.json")
    logo_dir = root / "logo"
    logo_dir.mkdir(exist_ok=True)

    todo = [c for c in channels if not (c.get("tvg_logo") or "").strip()]
    if args.limit:
        todo = todo[: args.limit]
    print(f"待补台标: {len(todo)} 个（标准表 {len(channels)}）")

    sem = asyncio.Semaphore(args.concurrency)
    results: dict[int, tuple[str, bytes | None]] = {}

    async def worker(idx: int, ch: dict[str, Any]) -> None:
        async with sem:
            results[idx] = await grab(ch)

    await asyncio.gather(*(worker(i, c) for i, c in enumerate(todo)))

    got, miss = 0, []
    for idx, ch in enumerate(todo):
        key, data = results.get(idx, ("", None))
        if data and key:
            (logo_dir / f"{key}.png").write_bytes(data)
            ch["tvg_logo"] = f"https://cdn.jsdelivr.net/gh/Hawaiine/Oasisic-IPTV@main/logo/{quote(key)}.png"
            if not ch.get("tvg_id"):
                ch["tvg_id"] = key
            got += 1
        else:
            miss.append(f"{ch.get('standard_name')} | {ch.get('category')} | logo-missing（上游镜像无此台标）")

    save_text(root / "data" / "channels.json", json.dumps(channels, ensure_ascii=False, indent=4) + "\n")
    if miss:
        path = root / "data" / "logo_missing.txt"
        header = path.read_text(encoding="utf-8") if path.exists() else ""
        lines = [ln for ln in header.splitlines() if ln.strip() and not ln.startswith("#")]
        merged = sorted(set(lines + miss))
        save_text(
            path,
            "# 缺失台标清单（有上游即补；无上游写明尝试来源与结果）\n"
            "# 格式：标准名 | 分类 | 原因\n" + "\n".join(merged) + "\n",
        )
    print(f"✅ 补到 {got} 个台标，仍缺 {len(miss)} 个（已写入 data/logo_missing.txt）")


if __name__ == "__main__":
    asyncio.run(main())