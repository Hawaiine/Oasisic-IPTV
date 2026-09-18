#!/usr/bin/env python3
"""每周可播报告：读取 output/health.json，输出分类汇总 + 建议。

用法：
  python scripts/weekly_playability_report.py            # 终端输出
  python scripts/weekly_playability_report.py --discord   # 推送 Discord
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from datetime import datetime, timezone, timedelta
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
HEALTH_PATH = REPO / "output" / "health.json"


def load_health(path: Path) -> dict:
    if not path.exists():
        print(f"❌ 未找到 {path}")
        print("   请先运行: python scripts/probe.py --egress-label <label>")
        sys.exit(1)
    return json.loads(path.read_text(encoding="utf-8"))


def summarize(data: dict) -> str:
    now = datetime.now(timezone.utc)
    generated = datetime.fromisoformat(data.get("generated_at", "").replace("Z", "+00:00"))
    age_days = (now - generated).days
    tz = data.get("timezone", "UTC")
    egress = data.get("egress_label", "unknown")
    channels = data.get("channels", [])
    total = len(channels)
    grade_counts = Counter(ch.get("grade", "unknown") for ch in channels)
    ok = grade_counts.get("ok", 0)
    ratio = ok / total if total else 0.0

    lines = [
        "## 📊 每周可播报告",
        "",
        f"- 生成时间: {generated.strftime('%Y-%m-%d %H:%M %Z')} ({tz})",
        f"- 探测出口: {egress}",
        f"- 数据年龄: {age_days} 天",
        f"- 探测总数: {total}",
        f"- 可播: {ok} ({ratio:.1%})",
        "",
        "### 分级分布",
        "",
        "| 分级 | 数量 | 占比 |",
        "|------|------|------|",
    ]
    for grade in ["ok", "playlist-missing", "http-error", "timeout", "http-403", "http-404", "ssl-fail", "conn-fail", "dns-fail", "ipv6-no-route", "rtp", "unknown"]:
        n = grade_counts.get(grade, 0)
        if n:
            lines.append(f"| {grade} | {n} | {n/total:.1%} |")
    lines += [
        "",
        "### 建议",
        "",
    ]
    if ratio < 0.5:
        lines.append("- ⚠️ 可播率低于 50%，建议检查本地网络到源站的连通性")
    if age_days > 7:
        lines.append("- ⚠️ 数据已超过 7 天，建议重新运行 probe.py")
    if grade_counts.get("timeout", 0) > total * 0.3:
        lines.append("- ⚠️ 超时占比高，建议检查 DNS 或切换网络")
    if grade_counts.get("http-403", 0) > 0:
        lines.append("- ℹ️ 发现网络锁源（403），已记录在 live_cmcc.m3u")
    if grade_counts.get("ipv6-no-route", 0) > 0:
        lines.append("- ℹ️ 发现 IPv6 源（当前出口不可达），已记录在 live_ipv6.m3u")
    if not lines[-1].startswith("-"):
        lines.append("- ✅ 数据新鲜，可播率正常")
    lines.append("")
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description="每周可播报告")
    parser.add_argument("--discord", action="store_true", help="推送到 Discord")
    args = parser.parse_args()

    data = load_health(HEALTH_PATH)
    report = summarize(data)
    print(report)

    if args.discord:
        try:
            sys.path.insert(0, str(REPO / "scripts"))
            from send_discord import send_discord_message  # type: ignore

            send_discord_message(report)
            print("✅ 已推送到 Discord")
        except Exception as exc:
            print(f"❌ Discord 推送失败: {exc}")


if __name__ == "__main__":
    main()
