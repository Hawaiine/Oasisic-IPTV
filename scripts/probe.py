#!/usr/bin/env python3
"""探活：对列表里的 URL 做真实可达性探测 → output/health.json + 网络类型分列。

设计约束（与 collect 解耦，纯旁路）：
- 不改动采集链路；health.json 不存在时 select.py 行为与旧版完全一致。
- 探活只读首片（Range 请求），不下载整段流。
- 结果只代表「探测出口网络」，health.json 里记录 egress 标签，不冒充全国可用。

用法：
    python scripts/probe.py                      # 探 config/probe.yaml 的默认列表
    python scripts/probe.py --input output/live_more.m3u --limit 500
    python scripts/probe.py --egress-label wuhan-unicom
"""

from __future__ import annotations

import argparse
import asyncio
import socket
import sys
import time
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any
from urllib.parse import urljoin

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from lib.health import (  # noqa: E402
    CST,
    HTTP_403,
    OK,
    PLAYLIST_MISSING,
    UNKNOWN,
    build_index,
    grade,
    is_cmcc_host,
    is_ipv6_literal,
    is_signed,
    level_rank,
    looks_like_playlist,
    summarize,
)
from lib.io_util import load_yaml, project_root, save_json, save_text  # noqa: E402
from lib.m3u import build_m3u, parse_m3u  # noqa: E402

DEFAULT_CFG: dict[str, Any] = {
    "inputs": ["output/live.m3u", "output/live_backup.m3u"],
    "concurrency": 24,
    "timeout_sec": 8,
    "body_bytes": 2048,
    "follow_redirects": True,
    "verify_ssl": False,
    "probe_segment": True,
    "max_age_days": 7,
    "health_file": "output/health.json",
    "write_columns": True,
    "egress_label": "local",
    "record_ip": False,
}

# 用于判断本机是否有 IPv6 出口（阿里公共 DNS / Google DNS 的 v6 地址）
IPV6_PROBE_TARGETS = (("2400:3200:baba::1", 53), ("2001:4860:4860::8888", 53))


def load_probe_config() -> dict[str, Any]:
    path = project_root() / "config" / "probe.yaml"
    cfg = dict(DEFAULT_CFG)
    if path.exists():
        cfg.update(load_yaml(path) or {})
    return cfg


def load_settings() -> dict[str, Any]:
    path = project_root() / "config" / "settings.yaml"
    return load_yaml(path) if path.exists() else {}


def now_cst() -> str:
    return datetime.now(CST).strftime("%Y-%m-%d %H:%M:%S")


def collect_urls(paths: list[Path]) -> list[dict[str, Any]]:
    """从多个 M3U 读条目，按 URL 去重（保留首次出现）。"""
    seen: dict[str, dict[str, Any]] = {}
    for p in paths:
        if not p.exists():
            print(f"⚠ 跳过不存在的列表：{p}")
            continue
        entries = parse_m3u(p.read_text(encoding="utf-8"))
        for e in entries:
            url = e.get("url") or ""
            if url and url not in seen:
                seen[url] = e
        print(f"  {p.name}: {len(entries)} 条")
    return list(seen.values())


async def detect_ipv6_egress(timeout: float = 3.0) -> bool:
    """本机能否建立 IPv6 TCP 连接（决定 ipv6-no-route 分级是否有意义）。"""
    loop = asyncio.get_running_loop()
    for host, port in IPV6_PROBE_TARGETS:
        sock = socket.socket(socket.AF_INET6, socket.SOCK_STREAM)
        sock.setblocking(False)
        try:
            await asyncio.wait_for(loop.sock_connect(sock, (host, port)), timeout=timeout)
            return True
        except Exception:  # noqa: BLE001
            continue
        finally:
            sock.close()
    return False


async def _one_probe(
    session: Any,
    url: str,
    *,
    timeout: float,
    body_bytes: int,
    probe_segment: bool,
) -> dict[str, Any]:
    """单 URL 探测 → {level, status, latency_ms, detail, signed}。"""
    t0 = time.perf_counter()
    rec: dict[str, Any] = {
        "level": UNKNOWN,
        "status": 0,
        "latency_ms": 0,
        "detail": "",
        "signed": is_signed(url),
        "ipv6_literal": is_ipv6_literal(url),
        "cmcc_host": is_cmcc_host(url),
    }
    try:
        import aiohttp

        async with session.get(
            url,
            headers={"Range": f"bytes=0-{max(0, body_bytes - 1)}", "User-Agent": session.headers["User-Agent"]},
            timeout=aiohttp.ClientTimeout(total=timeout),
        ) as resp:
            head = await resp.content.read(body_bytes)
            rec["status"] = resp.status
            level = grade(url=url, status=resp.status, body_head=head)
            if level == PLAYLIST_MISSING and probe_segment:
                seg = await _probe_first_segment(
                    session, url, head, body_head=head, timeout=timeout
                )
                if seg:
                    level = seg
                    rec["detail"] = "segment-ok" if seg == OK else f"segment-{seg}"
            rec["level"] = level
    except Exception as exc:  # noqa: BLE001
        rec["level"] = grade(
            url=url, error_type=type(exc).__name__, error_msg=str(exc)
        )
        rec["detail"] = f"{type(exc).__name__}: {str(exc)[:80]}"
    rec["latency_ms"] = int((time.perf_counter() - t0) * 1000)
    return rec


async def _probe_first_segment(
    session: Any, url: str, head: bytes, *, body_head: bytes = b"", timeout: float = 8
) -> str | None:
    """m3u8 返回 200 但不是播放列表时，尝试解析出第一个分片再探一次。"""
    text = head.decode("utf-8", "replace")
    target = ""
    for line in text.splitlines():
        line = line.strip()
        if line and not line.startswith("#"):
            target = line
            break
    if not target or target.startswith("<"):  # HTML 页面
        return None
    seg_url = urljoin(url, target)
    try:
        import aiohttp

        async with session.get(
            seg_url,
            headers={"Range": "bytes=0-2047", "User-Agent": session.headers["User-Agent"]},
            timeout=aiohttp.ClientTimeout(total=timeout),
        ) as resp:
            body = await resp.content.read(2048)
            if resp.status in (200, 206) and looks_like_playlist(body):
                return OK
            return PLAYLIST_MISSING
    except Exception:  # noqa: BLE001
        return None


async def probe_all(
    urls: list[str],
    *,
    cfg: dict[str, Any],
    ua: str,
) -> tuple[dict[str, dict[str, Any]], bool]:
    import aiohttp

    sem = asyncio.Semaphore(max(1, int(cfg.get("concurrency") or 24)))
    timeout = float(cfg.get("timeout_sec") or 8)
    body_bytes = int(cfg.get("body_bytes") or 2048)
    probe_segment = bool(cfg.get("probe_segment", True))

    connector = aiohttp.TCPConnector(
        limit=max(1, int(cfg.get("concurrency") or 24)),
        ssl=bool(cfg.get("verify_ssl", False)),
    )
    results: dict[str, dict[str, Any]] = {}
    done = 0

    async with aiohttp.ClientSession(
        connector=connector,
        headers={"User-Agent": ua},
        timeout=aiohttp.ClientTimeout(total=timeout),
    ) as session:
        v6 = await detect_ipv6_egress()

        async def worker(url: str) -> None:
            nonlocal done
            async with sem:
                results[url] = await _one_probe(
                    session,
                    url,
                    timeout=timeout,
                    body_bytes=body_bytes,
                    probe_segment=probe_segment,
                )
            done += 1
            if done % 25 == 0 or done == len(urls):
                print(f"  探测进度 {done}/{len(urls)}")

        await asyncio.gather(*(worker(u) for u in urls))
    return results, v6


def write_columns(
    entries: list[dict[str, Any]],
    results: dict[str, dict[str, Any]],
    cfg: dict[str, Any],
    *,
    url_tvg: str,
    out_dir: Path | None = None,
    max_keep_per_name: int = 3,
) -> dict[str, int]:
    """按链路类型生成分列：IPv6 专列 / 网络锁专列 / 时效签名专列。

    分列是「链路类型问题清单」，不是订阅主列表：同一频道最多保留 `max_keep_per_name` 条，
    便于对应网络的用户自己在同类链接里做故障转移（与 live_backup 口径一致）。
    """
    titles = cfg.get("column_titles") or {}
    out_dir = out_dir or (project_root() / (cfg.get("output_dir") or "output/"))
    buckets: dict[str, list[dict[str, Any]]] = {"ipv6": [], "cmcc": [], "signed": []}
    seen: dict[str, set[str]] = {"ipv6": set(), "cmcc": set(), "signed": set()}
    per_name: dict[str, Counter[str]] = {k: Counter() for k in buckets}

    def _add(kind: str, entry: dict[str, Any], url: str) -> None:
        if url in seen[kind]:
            return
        name = entry.get("name") or entry.get("display_name") or url
        if per_name[kind][name] >= max_keep_per_name:
            return
        per_name[kind][name] += 1
        seen[kind].add(url)
        buckets[kind].append(entry)

    for e in entries:
        url = e.get("url") or ""
        if not url:
            continue
        rec = results.get(url) or {}
        level = str(rec.get("level") or UNKNOWN)
        if is_ipv6_literal(url) and level != OK:
            _add("ipv6", e, url)
        if level == HTTP_403:
            _add("cmcc", e, url)
        if is_signed(url):
            _add("signed", e, url)

    counts: dict[str, int] = {}
    for key, items in buckets.items():
        rows = []
        for e in items:
            row = dict(e)
            row["group_title"] = row.get("group") or row.get("group_title") or ""
            rows.append(row)
        title = titles.get(key) or f"Oasisic-IPTV {key}"
        save_text(
            out_dir / f"live_{key}.m3u",
            build_m3u(rows, playlist_title=title, url_tvg=url_tvg),
        )
        counts[key] = len(rows)
    return counts


async def run(args: argparse.Namespace) -> int:
    cfg = load_probe_config()
    if args.concurrency:
        cfg["concurrency"] = args.concurrency
    if args.timeout:
        cfg["timeout_sec"] = args.timeout
    if args.egress_label:
        cfg["egress_label"] = args.egress_label
    root = project_root()
    settings = load_settings()
    ua = settings.get("user_agent") or "Oasisic-IPTV/1.0"
    url_tvg = settings.get("url_tvg") or "https://live.fanmingming.com/e.xml"

    inputs = args.input or [root / p for p in (cfg.get("inputs") or [])]
    inputs = [Path(p) if Path(p).is_absolute() else root / p for p in inputs]
    if args.include_more:
        inputs.append(root / "output" / "live_more.m3u")

    print("== Oasisic-IPTV probe ==")
    print(f"出口标签: {cfg.get('egress_label')} | 并发 {cfg.get('concurrency')} | 超时 {cfg.get('timeout_sec')}s")
    print("读取列表:")
    entries = collect_urls(inputs)
    urls = [e.get("url") or "" for e in entries]
    if args.limit:
        urls = urls[: args.limit]
        entries = entries[: args.limit]
    if not urls:
        print("❌ 没有可探测的 URL")
        return 1
    print(f"待探测 URL: {len(urls)}（按 URL 去重）")

    results, ipv6_egress = await probe_all(urls, cfg=cfg, ua=ua)

    counts: Counter[str] = Counter(str(r.get("level")) for r in results.values())
    print("\n== 分级结果 ==")
    for level, n in sorted(counts.items(), key=lambda kv: (level_rank(kv[0]), kv[0])):
        print(f"  {level:18s} {n}")
    print(f"IPv6 出口: {'有' if ipv6_egress else '无（v6-only 链接本机不可达）'}")

    payload: dict[str, Any] = {
        "schema_version": 1,
        "stage": "probe",
        "generated_at": now_cst(),
        "timezone": "Asia/Shanghai",
        "egress": {
            "label": str(cfg.get("egress_label") or "local"),
            "ipv6_egress": bool(ipv6_egress),
        },
        "config": {
            "timeout_sec": cfg.get("timeout_sec"),
            "concurrency": cfg.get("concurrency"),
            "body_bytes": cfg.get("body_bytes"),
            "probe_segment": cfg.get("probe_segment"),
            "max_age_days": cfg.get("max_age_days"),
        },
        "checked": len(results),
        "counts": dict(counts),
        "urls": results,
    }
    if cfg.get("record_ip"):
        payload["egress"]["ip"] = _public_ip()

    health_path = root / str(cfg.get("health_file") or "output/health.json")
    save_json(health_path, payload)
    print(f"\n✅ 写入 {health_path.relative_to(root)}（{len(results)} 条）")

    if cfg.get("write_columns", True) and not args.no_columns:
        col = write_columns(entries, results, cfg, url_tvg=url_tvg)
        print("✅ 分列: " + " ".join(f"live_{k}.m3u={v}" for k, v in col.items()))
    idx = build_index(payload, max_age_days=int(cfg.get("max_age_days") or 7))
    print(f"健康索引: {summarize(idx)}")
    return 0


def _public_ip() -> str:
    try:
        import urllib.request

        with urllib.request.urlopen("https://api.ipify.org", timeout=5) as resp:  # noqa: S310
            return resp.read().decode("utf-8", "replace").strip()
    except Exception:  # noqa: BLE001
        return ""


def main() -> None:
    parser = argparse.ArgumentParser(description="Oasisic-IPTV URL 探活（只读首片）")
    parser.add_argument("--input", action="append", help="要探测的 m3u 路径（可多次）")
    parser.add_argument("--include-more", action="store_true", help="追加探测 output/live_more.m3u")
    parser.add_argument("--limit", type=int, default=0, help="只探前 N 条（调试用）")
    parser.add_argument("--concurrency", type=int, default=0)
    parser.add_argument("--timeout", type=float, default=0)
    parser.add_argument("--egress-label", default="", help="出口网络标签，如 wuhan-unicom")
    parser.add_argument("--no-columns", action="store_true", help="不生成分列文件")
    args = parser.parse_args()
    try:
        raise SystemExit(asyncio.run(run(args)))
    except KeyboardInterrupt:
        print("中断")
        raise SystemExit(130)


if __name__ == "__main__":
    main()