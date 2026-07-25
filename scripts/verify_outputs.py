# coding: utf-8
"""
Oasisic-IPTV 输出验证脚本。

检查
----
1. output/live.m3u + output/check_result.json 存在
2. check_result.json schema_version == 1, stage 合法, generated_at 可解析
3. live.m3u 中 ``group-title="电台"`` 计数为 0
4. group_title 必须为规范中文分类名（来自 categories 模块）
5. 若存在 output/guide.xml，检查 well-formed XML 开头
6. 警告：other 占比 > 85% 且 total > 50 时 exit 1
"""

from __future__ import annotations

import datetime
import json
import os
import re
import sys
import typing as t

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


def main() -> None:
    root = project_root()
    output_dir = os.path.join(root, "output")

    errors: list[str] = []
    warnings: list[str] = []

    allowed = _allowed_group_titles()

    # ── 1. Required files exist ─────────────────────────────────
    live_path = os.path.join(output_dir, "live.m3u")
    check_path = os.path.join(output_dir, "check_result.json")

    if not os.path.isfile(live_path):
        errors.append("缺少 output/live.m3u")
    if not os.path.isfile(check_path):
        errors.append("缺少 output/check_result.json")

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

    print(f"✅ check_result.json: schema_version={check['schema_version']}, "
          f"stage={check['stage']}, total={check.get('total')}")

    # ── 3. live.m3u: radio must be absent ───────────────────────
    with open(live_path, "r", encoding="utf-8", errors="replace") as f:
        live_text = f.read()

    radio_count = len(re.findall(r'group-title="电台"', live_text))
    if radio_count > 0:
        errors.append(f"live.m3u 含 {radio_count} 条 group-title=\"电台\"，应为 0")

    if errors:
        _exit("❌ " + "\n   ".join(errors))

    print(f"✅ live.m3u: radio 计数 = {radio_count}")

    # Group-title must be canonical (only check the first group-title attr per EXTINF line)
    found_groups = set()
    for line in live_text.splitlines():
        if line.startswith("#EXTINF:"):
            # Extract only the first group-title attribute (before the comma)
            before_comma = line.split(",", 1)[0] if "," in line else line
            m = re.search(r'group-title="([^"]+)"', before_comma)
            if m:
                found_groups.add(m.group(1))
    bad_groups = {g for g in found_groups if g not in allowed}
    if bad_groups:
        # Sort for deterministic output
        sorted_bad = sorted(bad_groups)[:30]  # show at most 30
        msg = f"live.m3u 含非规范 group_title: {sorted_bad} (共 {len(bad_groups)} 个)"
        errors.append(msg)

    if errors:
        _exit("❌ " + "\n   ".join(errors))

    print(f"✅ live.m3u: group_title 全部规范")

    # ── 5. guide.xml well-formed check (if exists) ──────────────
    guide_path = os.path.join(output_dir, "guide.xml")
    if os.path.isfile(guide_path):
        with open(guide_path, "r", encoding="utf-8", errors="replace") as f:
            first_line = f.readline().strip()
        if first_line.startswith("<?xml") or first_line.startswith("<tv"):
            print(f"✅ guide.xml: 存在且格式正确")
        else:
            warnings.append(f"⚠️ guide.xml 开头异常: {first_line[:60]}")
    else:
        print(f"ℹ️  guide.xml 不存在（EPG 默认不提交）")

    # ── 6. Other ratio check ────────────────────────────────────
    total = check.get("total", 0)
    if total > 50:
        other_count = 0
        for line in live_text.splitlines():
            if 'group-title="其他"' in line:
                other_count += 1
        other_ratio = other_count / total * 100
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