#!/usr/bin/env python3
"""Discord 通知。Webhook 只从环境变量读取，仓库内不得出现真实地址。"""

from __future__ import annotations

import json
import os
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from lib.io_util import load_json, project_root  # noqa: E402

UA = "HermesAgent/1.0"


def main() -> None:
    url = os.environ.get("DISCORD_WEBHOOK") or os.environ.get("DISCORD_WEBHOOK_URL") or ""
    if not url:
        print("未设置 DISCORD_WEBHOOK，跳过通知")
        return
    if "discord.com/api/webhooks" not in url and "discordapp.com/api/webhooks" not in url:
        print("DISCORD_WEBHOOK 看起来不是 Discord Webhook，已拒绝发送")
        sys.exit(1)

    extra = (os.environ.get("DISCORD_MESSAGE") or "").strip()
    result_path = project_root() / "output" / "check_result.json"
    if extra:
        content = extra
    elif not result_path.exists():
        print("没有 check_result.json，跳过")
        return
    else:
        data = load_json(result_path)
        ok_n = data.get("ok") or 0
        fail_n = data.get("fail") or 0
        catalog = data.get("catalog") or 0
        more = data.get("more") or 0
        ratio = float(data.get("ratio") or 0)
        emoji = "✅" if fail_n == 0 else "⚠️"
        content = (
            f"{emoji} Oasisic-IPTV 日更 {data.get('generated_at', '')}\n"
            f"源 {ok_n}/{ok_n + fail_n} ({ratio:.0%}) · catalog={catalog} · more={more}"
        )
    payload = json.dumps({"content": content[:1900]}, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=payload,
        headers={"Content-Type": "application/json", "User-Agent": UA},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            print(f"Discord 通知已发送 HTTP {resp.status}")
    except Exception as exc:  # noqa: BLE001
        print(f"Discord 通知失败: {exc}")
        sys.exit(0)  # 通知失败不阻断流水线


if __name__ == "__main__":
    main()
