# coding: utf-8
"""
Oasisic-IPTV 输出验证脚本（D2：目录制双列表）。

检查
----
1. output/live.m3u + output/check_result.json 存在
2. check_result.json schema_version, stage, generated_at
3. live.m3u 中 radio 计数为 0
4. group_title 必须为规范中文分类名
5. live.m3u: entries == unique_names == unique_urls（max/名=1）
6. live_more.m3u 存在
7. probe 模式：live_verified.m3u 存在
8. other 占比检查
"""

from __future__ import annotations

import datetime
import json
import os
import re
import sys
import typing as t
from collections import Counter

_SCRIPTS_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__)))
if _SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, _SCRIPTS_DIR)

from lib import categories as cat
from lib.io_util import project_root


def _exit(msg: str, code: int = 1) -> None:
    print(msg)
    sys.exit(code)


def _allowed_group_titles() -> set[str]:
    """Return the set of canonical Chinese group titles."""
    return {cat.group_title(k) for k in cat.all_categories()}


def _parse_m3u(path: str) -> tuple[list[str], list[str]]:
    """Parse M3U file, return (names, urls)."""
    names: list[str] = []
    urls: list[str] = []
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        for line in f:
            line = line.strip()
            if line.startswith("#EXTINF:"):
                if "," in line:
                    name = line.split(",", 1)[1].strip()
                    names.append(name)
            elif line and not line.startswith("#"):
                urls.append(line)
    return names, urls


def main() -> None:
    root = project_root()
    output_dir = os.path.join(root, "output")

    errors: list[str] = []
    warnings: list[str] = []

    allowed = _allowed_group_titles()

    # ── 1. Required files exist ─────────────────────────────────
    live_path = os.path.join(output_dir, "live.m3u")
    check_path = os.path.join(output_dir, "check_result.json")
    more_path = os.path.join(output_dir, "live_more.m3u")

    if not os.path.isfile(live_path):
        errors.append("缺少 output/live.m3u")
    if not os.path.isfile(check_path):
        errors.append("缺少 output/check_result.json")
    if not os.path.isfile(more_path):
        errors.append("缺少 output/live_more.m3u（D2 必须）")

    if errors:
        _exit("❌ " + "\n   ".join(errors))

    # ── 2. check_result.json ────────────────────────────────────
    with open(check_path, "r", encoding="utf-8") as f:
        check = json.load(f)

    if check.get("schema_version") != 1:
        errors.append(f"schema_version={check.get('schema_version')} 应为 1")
    if check.get("stage") not in ("collect", "probe"):
        errors.append(f"stage={check.get('stage')} 应为 collect 或 probe")

    generated_at = check.get("generated_at", "")
    try:
        datetime.datetime.strptime(generated_at, "%Y-%m-%d %H:%M:%S")
    except (ValueError, TypeError):
        errors.append(f"generated_at 不可解析: {generated_at}")

    if errors:
        _exit("❌ check_result.json 校验失败:\n   " + "\n   ".join(errors))

    print(f"✅ check_result.json: schema={check['schema_version']}, "
          f"stage={check['stage']}, total={check.get('total')}, "
          f"catalog={check.get('catalog_count', '?')}, more={check.get('more_count', '?')}")

    # ── 3. live.m3u: radio must be absent ───────────────────────
    with open(live_path, "r", encoding="utf-8", errors="replace") as f:
        live_text = f.read()

    radio_count = len(re.findall(r'group-title="电台"', live_text))
    if radio_count > 0:
        errors.append(f"live.m3u 含 {radio_count} 条 group-title=\"电台\"，应为 0")
        _exit("❌ " + "\n   ".join(errors))

    print(f"✅ live.m3u: radio 计数 = {radio_count}")

    # ── 4. live.m3u: entries == unique names == unique URLs ─────
    names, urls = _parse_m3u(live_path)
    name_counts = Counter(names)
    url_counts = Counter(urls)

    max_per_name = max(name_counts.values()) if name_counts else 0
    dup_names = sum(1 for v in name_counts.values() if v > 1)
    dup_urls = sum(1 for v in url_counts.values() if v > 1)

    print(f"   live.m3u: {len(names)} 条, 唯一名 {len(set(names))}, "
          f"唯一 URL {len(set(urls))}, max/名={max_per_name}")

    if max_per_name > 1:
        errors.append(f"live.m3u max/名={max_per_name}，应为 1（目录制）")
    if dup_names > 0:
        errors.append(f"live.m3u 同名多链 {dup_names} 个，应为 0")
    if dup_urls > 0:
        errors.append(f"live.m3u 重复 URL 组 {dup_urls} 个，应为 0")

    # ── 5. Group-title must be canonical ────────────────────────
    found_groups = set()
    for line in live_text.splitlines():
        if line.startswith("#EXTINF:"):
            before_comma = line.split(",", 1)[0] if "," in line else line
            m = re.search(r'group-title="([^"]+)"', before_comma)
            if m:
                found_groups.add(m.group(1))
    bad_groups = {g for g in found_groups if g not in allowed}
    if bad_groups:
        sorted_bad = sorted(bad_groups)[:30]
        msg = f"live.m3u 含非规范 group_title: {sorted_bad} (共 {len(bad_groups)} 个)"
        errors.append(msg)

    if errors:
        _exit("❌ " + "\n   ".join(errors))

    print(f"✅ live.m3u: group_title 全部规范，max/名=1，无重复 URL")

    # ── 6. live_more.m3u exists and has entries ─────────────────
    more_names, more_urls = _parse_m3u(more_path)
    if len(more_names) > 0:
        print(f"✅ live_more.m3u: {len(more_names)} 条")
    else:
        warnings.append("⚠️  live_more.m3u 为空")

    # ── 7. Probe mode: live_verified.m3u ────────────────────────
    probe_mode = check.get("probe_enabled") or check.get("stage") == "probe"
    verified_path = os.path.join(output_dir, "live_verified.m3u")
    if probe_mode:
        if not os.path.isfile(verified_path):
            errors.append("probe 模式下缺少 output/live_verified.m3u")
        else:
            from lib.m3u import count_extinf
            vc = count_extinf(verified_path)
            print(f"✅ live_verified.m3u: {vc} 条")

    if errors:
        _exit("❌ " + "\n   ".join(errors))

    # ── 8. Other ratio check ────────────────────────────────────
    total = len(names)
    if total > 50:
        other_count = 0
        for line in live_text.splitlines():
            if 'group-title="其他"' in line:
                other_count += 1
        other_ratio = other_count / total * 100 if total else 0
        if other_ratio > 85:
            _exit(f"❌ other 占比 {other_ratio:.0f}% > 85% (total={total})")
        elif other_ratio > 70:
            warnings.append(f"⚠️ other 占比 {other_ratio:.0f}% 偏高")
        else:
            print(f"✅ other 占比 {other_ratio:.0f}%")

    for w in warnings:
        print(w)

    print("✅ 验证通过" + (" (有警告)" if warnings else ""))


if __name__ == "__main__":
    main()