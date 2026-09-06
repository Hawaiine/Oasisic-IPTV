#!/usr/bin/env python3
"""根据 check_result.json 生成采集报告（追加 CHANGELOG 顶部）。"""

from __future__ import annotations

import argparse
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from lib.io_util import load_json, project_root  # noqa: E402
from lib.m3u import parse_m3u  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--write-changelog", action="store_true", help="写入 CHANGELOG 顶部")
    args = parser.parse_args()
    root = project_root()
    result = load_json(root / "output" / "check_result.json")
    live = (root / "output" / "live.m3u").read_text(encoding="utf-8")
    entries = parse_m3u(live)
    groups = Counter(e.get("group") or "其他" for e in entries)
    lines = [
        f"## 采集报告 {result.get('generated_at', '')}",
        "",
        f"- 状态: catalog={result.get('catalog')} / more={result.get('more')} / radio={result.get('radio')}",
        f"- 源成功率: {result.get('ok')}/{result.get('ok', 0) + result.get('fail', 0)} ({float(result.get('ratio') or 0):.0%})",
        f"- 时区: {result.get('timezone')}",
        "",
        "| 分类 | 条数 |",
        "|------|------|",
    ]
    for g, n in groups.most_common():
        lines.append(f"| {g} | {n} |")
    lines.append("")
    report = "\n".join(lines)
    print(report)
    if args.write_changelog:
        path = root / "CHANGELOG.md"
        old = path.read_text(encoding="utf-8") if path.exists() else "# CHANGELOG\n"
        if report.strip() in old:
            print("CHANGELOG 已包含本次报告，跳过")
            return
        path.write_text(report + "\n---\n\n" + old.lstrip(), encoding="utf-8")
        print("✅ 已写入 CHANGELOG.md")


if __name__ == "__main__":
    main()
