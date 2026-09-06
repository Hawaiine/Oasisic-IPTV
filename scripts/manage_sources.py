#!/usr/bin/env python3
"""源生命周期管理：list / validate / stats / enable / disable。"""

from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from lib.io_util import load_json, load_yaml, project_root  # noqa: E402
from lib.m3u import parse_playlist  # noqa: E402

ALLOWED_TYPES = {"m3u", "txt"}
ALLOWED_REGIONS = {"cn", "hk_tw", "overseas", "hotel", "radio"}


def load_sources() -> list[dict[str, Any]]:
    data = load_yaml(project_root() / "config" / "sources.yaml")
    return list(data.get("sources") or [])


def source_key(s: dict[str, Any]) -> str:
    return str(s.get("key") or s.get("name") or "")


def cmd_list(_args: argparse.Namespace) -> int:
    sources = load_sources()
    stats_path = project_root() / "data" / "source_stats.json"
    stats: dict[str, Any] = {}
    if stats_path.exists():
        try:
            stats = (load_json(stats_path).get("sources") or {})
        except Exception:  # noqa: BLE001
            stats = {}
    print(f"{'KEY':<22} {'ON':<4} {'CORE':<5} {'REGION':<8} {'PRIO':<5} {'LAST':<12} {'ERR'}")
    for s in sources:
        key = source_key(s)
        st = stats.get(key) or {}
        last = st.get("last_ok") or st.get("last_fail") or "-"
        err = (st.get("last_error") or "")[:40]
        on = "yes" if s.get("enabled", True) else "no"
        core = "yes" if s.get("core") else ""
        print(
            f"{key:<22} {on:<4} {core:<5} {s.get('region',''):<8} "
            f"{int(s.get('priority') or 50):<5} {last:<12} {err}"
        )
    print(f"合计 {len(sources)} 个源")
    return 0


def cmd_validate(args: argparse.Namespace) -> int:
    sources = load_sources()
    errors: list[str] = []
    keys: set[str] = set()
    urls: set[str] = set()
    for i, s in enumerate(sources):
        key = source_key(s)
        url = (s.get("url") or "").strip()
        stype = (s.get("type") or "").lower()
        region = s.get("region") or ""
        if not key:
            errors.append(f"[{i}] 缺少 key/name")
        elif key in keys:
            errors.append(f"[{i}] 重复 key: {key}")
        keys.add(key)
        if not url:
            errors.append(f"[{key}] 空 URL")
        else:
            p = urlparse(url)
            if p.scheme not in {"http", "https"} or not p.netloc:
                errors.append(f"[{key}] 非法 URL: {url}")
            if url in urls:
                errors.append(f"[{key}] 重复 URL")
            urls.add(url)
        if stype not in ALLOWED_TYPES:
            errors.append(f"[{key}] type 必须是 m3u|txt，实际 {stype!r}")
        if region and region not in ALLOWED_REGIONS:
            errors.append(f"[{key}] 未知 region: {region}")

    if errors:
        print("❌ 校验失败:")
        for e in errors:
            print(f"  {e}")
        return 1

    print(f"✅ 模式校验通过: {len(sources)} 个源")
    if not getattr(args, "online", False):
        return 0

    # 在线检查源 URL 可访问性与返回频道数（不是检测直播流）
    return asyncio.run(_validate_online(sources))


# 在线校验：有效频道数低于此值视为「内容为空列表」异常
EMPTY_LIST_THRESHOLD = 5


async def _validate_online(sources: list[dict[str, Any]]) -> int:
    import aiohttp

    settings = load_yaml(project_root() / "config" / "settings.yaml")
    timeout = int(settings.get("request_timeout_sec") or 30)
    ua = settings.get("user_agent") or "Oasisic-IPTV/1.0"
    fail = 0
    connector = aiohttp.TCPConnector(limit=8, ssl=False)
    async with aiohttp.ClientSession(connector=connector) as session:
        for s in sources:
            if not s.get("enabled", True):
                print(f"  – {source_key(s)}: disabled")
                continue
            key = source_key(s)
            core = bool(s.get("core"))
            try:
                async with session.get(
                    s["url"],
                    timeout=aiohttp.ClientTimeout(total=timeout),
                    headers={"User-Agent": ua},
                ) as resp:
                    if resp.status != 200:
                        print(f"  ✗ {key}: HTTP {resp.status}")
                        fail += 1
                        continue
                    text = await resp.text(errors="replace")
                    entries = parse_playlist(text, (s.get("type") or "m3u"))
                    head = text.lstrip()[:16]
                    if (s.get("type") or "m3u") == "m3u" and not (
                        head.startswith("#EXTM3U") or "#EXTINF" in text[:400]
                    ) and not entries:
                        print(f"  ✗ {key}: 非 M3U 且无条目")
                        fail += 1
                        continue
                    if len(entries) < EMPTY_LIST_THRESHOLD:
                        # 内容为空/接近为空：核心源只告警，非核心源按失败计
                        suffix = "（核心源仅告警）" if core else "（建议禁用）"
                        print(
                            f"  ⚠ {key}: 内容近乎为空（{len(entries)} 条 < {EMPTY_LIST_THRESHOLD}）"
                            f" {suffix}"
                        )
                        if not core:
                            fail += 1
                        continue
                    print(f"  ✓ {key}: HTTP 200, {len(entries)} 条")
            except Exception as exc:  # noqa: BLE001
                print(f"  ✗ {key}: {type(exc).__name__}: {exc}")
                fail += 1
    if fail:
        print(f"❌ 在线校验失败 {fail} 个源")
        return 1
    print("✅ 在线校验通过")
    return 0


def cmd_stats(_args: argparse.Namespace) -> int:
    path = project_root() / "data" / "source_stats.json"
    if not path.exists():
        print("尚无 source_stats.json，先跑一次 collect")
        return 0
    data = load_json(path)
    print(f"更新于 {data.get('updated_at', '-')}")
    print(
        f"{'KEY':<22} {'OK':>4} {'FAIL':>5} {'RATE':>6} {'STREAK':>6} "
        f"{'COUNT':>6} {'LAST_OK':<12} {'LAST_FAIL':<12} ERR"
    )
    rows = list((data.get("sources") or {}).items())
    rows.sort(key=lambda kv: (-(kv[1].get("ok") or 0), kv[0]))
    for key, rec in rows:
        ok_n = int(rec.get("ok") or 0)
        fail_n = int(rec.get("fail") or 0)
        total = ok_n + fail_n
        rate = f"{ok_n / total:.0%}" if total else "-"
        print(
            f"{key:<22} {ok_n:>4} {fail_n:>5} {rate:>6} "
            f"{int(rec.get('consecutive_fail') or 0):>6} "
            f"{int(rec.get('last_count') or 0):>6} "
            f"{(rec.get('last_ok') or '-'):<12} "
            f"{(rec.get('last_fail') or '-'):<12} "
            f"{(rec.get('last_error') or '')[:40]}"
        )
    return 0


def _set_enabled(key: str, enabled: bool) -> int:
    path = project_root() / "config" / "sources.yaml"
    lines = path.read_text(encoding="utf-8").splitlines(keepends=True)
    in_block = False
    found = False
    target = "true" if enabled else "false"
    for i, line in enumerate(lines):
        if line.strip().startswith("- key:") or line.strip().startswith("- name:"):
            in_block = key in line
            if in_block:
                found = True
        if in_block and "enabled:" in line:
            prefix, _, _rest = line.partition("enabled:")
            # 保留原缩进与注释
            comment = ""
            if "#" in line:
                comment = "  #" + line.split("#", 1)[1].rstrip("\n")
                if not comment.startswith("  #"):
                    comment = " #" + line.split("#", 1)[1].rstrip("\n")
            nl = "\n" if line.endswith("\n") else ""
            lines[i] = f"{prefix}enabled: {target}{comment}{nl}"
            in_block = False
    if not found:
        print(f"❌ 未找到源 {key}")
        return 1
    path.write_text("".join(lines), encoding="utf-8")
    print(f"✅ {key} enabled={target}")
    return 0


def cmd_enable(args: argparse.Namespace) -> int:
    return _set_enabled(args.key, True)


def cmd_disable(args: argparse.Namespace) -> int:
    return _set_enabled(args.key, False)


def main() -> None:
    parser = argparse.ArgumentParser(description="Oasisic-IPTV 源管理")
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("list", help="列出所有源及最近状态")
    p_val = sub.add_parser("validate", help="检查配置合法性；加 --online 探测可访问性")
    p_val.add_argument("--online", action="store_true")
    sub.add_parser("stats", help="查看采集成功率历史")
    p_en = sub.add_parser("enable", help="启用源")
    p_en.add_argument("key")
    p_dis = sub.add_parser("disable", help="禁用源")
    p_dis.add_argument("key")
    args = parser.parse_args()
    dispatch = {
        "list": cmd_list,
        "validate": cmd_validate,
        "stats": cmd_stats,
        "enable": cmd_enable,
        "disable": cmd_disable,
    }
    raise SystemExit(dispatch[args.cmd](args))


if __name__ == "__main__":
    main()
