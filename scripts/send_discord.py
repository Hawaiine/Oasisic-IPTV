# coding: utf-8
"""
Oasisic-IPTV Discord 通知脚本。

使用 Discord Webhook 发送采集报告 embed。

环境变量
--------
DISCORD_WEBHOOK 或 WEBHOOK_URL : str
    无此变量则打印 skip 并 exit 0。
"""

from __future__ import annotations

import json
import os
import sys
import typing as t
from urllib import request

_SCRIPTS_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__)))
if _SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, _SCRIPTS_DIR)

from lib.io_util import project_root
from lib.m3u import count_extinf

# ── Config ─────────────────────────────────────────────────────────

_WEBHOOK = os.environ.get("DISCORD_WEBHOOK") or os.environ.get("WEBHOOK_URL") or ""
_USER_AGENT = "HermesAgent/1.0"


def _build_embed() -> dict[str, t.Any]:
    """Build a Discord embed with per-file channel counts."""
    root = project_root()
    output_dir = os.path.join(root, "output")

    # ── Check result ────────────────────────────────────────────
    check_path = os.path.join(output_dir, "check_result.json")
    check = {}
    if os.path.isfile(check_path):
        with open(check_path, "r", encoding="utf-8") as f:
            check = json.load(f)

    # ── File counts ─────────────────────────────────────────────
    m3u_files: list[str] = sorted(
        f for f in os.listdir(output_dir) if f.endswith(".m3u")
    )
    field_lines: list[str] = []
    for fname in m3u_files:
        fpath = os.path.join(output_dir, fname)
        count = count_extinf(fpath)
        field_lines.append(f"**{fname}**: {count} 条")

    if not field_lines:
        field_lines.append("(无 M3U 文件)")

    # ── Embed ───────────────────────────────────────────────────
    total = check.get("total", "?")
    stage = check.get("stage", "collect")
    generated_at = check.get("generated_at", "")

    embed: dict[str, t.Any] = {
        "title": "📺 Oasisic-IPTV 采集报告",
        "color": 0x00BFFF,
        "fields": [
            {"name": "状态", "value": f"stage={stage}, total={total}", "inline": False},
            {"name": "生成时间", "value": generated_at or "N/A", "inline": True},
            {"name": "文件概览", "value": "\n".join(field_lines), "inline": False},
        ],
        "footer": {"text": "Oasisic-IPTV"},
    }

    if "generated_at" in check:
        embed["timestamp"] = generated_at

    return embed


def main() -> None:
    if not _WEBHOOK:
        print("⏭️  DISCORD_WEBHOOK 未设置，跳过通知")
        return

    embed = _build_embed()
    payload = json.dumps({"embeds": [embed]}).encode("utf-8")

    req = request.Request(
        _WEBHOOK,
        data=payload,
        headers={
            "Content-Type": "application/json",
            "User-Agent": _USER_AGENT,
        },
        method="POST",
    )

    try:
        with request.urlopen(req, timeout=15) as resp:
            if resp.status in (200, 204):
                print("✅ Discord 通知发送成功")
            else:
                print(f"⚠️  Discord 返回 HTTP {resp.status}")
    except Exception as exc:
        print(f"⚠️  Discord 通知失败: {exc}")


if __name__ == "__main__":
    main()