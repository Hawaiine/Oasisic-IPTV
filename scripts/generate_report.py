# coding: utf-8
"""
Oasisic-IPTV 工程报告生成脚本。

更新 CHANGELOG.md：时间、源成功率、live 条数、分类表、是否测活。
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

from lib.io_util import project_root
from lib.m3u import count_extinf


def _read_check_result() -> dict:
    path = os.path.join(project_root(), "output", "check_result.json")
    if not os.path.isfile(path):
        return {}
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _read_live_group_titles() -> dict[str, int]:
    """Count group_title occurrences in live.m3u."""
    path = os.path.join(project_root(), "output", "live.m3u")
    if not os.path.isfile(path):
        return {}
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        text = f.read()
    return dict(Counter(re.findall(r'group-title="([^"]+)"', text)).most_common())


def _build_report() -> str:
    check = _read_check_result()
    now = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=8)))
    ts = now.strftime("%Y-%m-%d %H:%M:%S")

    lines: list[str] = [
        f"## 📺 采集报告 ({ts})",
        "",
    ]

    # Basic stats
    total = check.get("total", "?")
    stage = check.get("stage", "collect")
    probe = check.get("probe_enabled", False)
    lines.append(f"- **状态**: stage={stage}, total={total}, probe_enabled={probe}")

    # Source success rate
    if "generated_at" in check:
        lines.append(f"- **生成时间**: {check.get('generated_at', '')}")

    # M3U file counts
    output_dir = os.path.join(project_root(), "output")
    m3u_files: list[str] = sorted(
        f for f in os.listdir(output_dir) if f.endswith(".m3u")
    )
    if m3u_files:
        lines.append("")
        lines.append("### 📁 文件概览")
        lines.append("")
        lines.append(f"| 文件 | 条数 |")
        lines.append(f"|------|------|")
        for fname in m3u_files:
            fpath = os.path.join(output_dir, fname)
            cnt = count_extinf(fpath)
            lines.append(f"| {fname} | {cnt} |")

    # Group-title distribution
    groups = _read_live_group_titles()
    if groups:
        lines.append("")
        lines.append("### 🏷️ 分类分布 (live.m3u)")
        lines.append("")
        lines.append(f"| 分类 | 条数 |")
        lines.append(f"|------|------|")
        for title, cnt in groups.items():
            lines.append(f"| {title} | {cnt} |")

    lines.append("")
    lines.append("---")
    lines.append("")

    return "\n".join(lines)


def main() -> None:
    report = _build_report()

    changelog_path = os.path.join(project_root(), "CHANGELOG.md")
    existing = ""
    if os.path.isfile(changelog_path):
        with open(changelog_path, "r", encoding="utf-8") as f:
            existing = f.read().strip()

    # Prepend new report, keep existing content below
    new_content = report + "\n\n" + existing if existing else report
    # Keep only the most recent 10 reports (roughly) by capping size
    # Method: find the 11th "---" separator and truncate
    parts = new_content.split("\n\n## 📺")
    if len(parts) > 11:
        parts = parts[:11]
        new_content = "## 📺".join(parts)

    with open(changelog_path, "w", encoding="utf-8") as f:
        f.write(new_content.strip() + "\n")

    print(f"✅ CHANGELOG.md 更新 ({len(new_content)} bytes)")


if __name__ == "__main__":
    main()