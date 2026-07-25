# coding: utf-8
"""
Oasisic-IPTV 源管理工具。

子命令
------
validate  — 检查 sources.yaml 的合法性（重复 key、空 URL、非法 URL）
list      — 列出所有源（含 disabled 状态）
disabled  — 列出已禁用的源
"""

from __future__ import annotations

import os
import re
import sys
from urllib.parse import urlparse

# Ensure scripts/ is on path
_SCRIPTS_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__)))
if _SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, _SCRIPTS_DIR)

from lib.io_util import load_yaml, project_root


def _get_sources() -> list[dict]:
    path = os.path.join(project_root(), "config", "sources.yaml")
    data = load_yaml(path)
    return data.get("sources", [])


def cmd_validate() -> None:
    """Validate sources.yaml: check for duplicate keys, empty URLs, malformed URLs."""
    sources = _get_sources()
    errors: list[str] = []

    names: list[str] = []
    urls: list[str] = []

    for i, src in enumerate(sources, start=1):
        name = src.get("name", "")
        url = src.get("url", "")

        # Check name presence
        if not name:
            errors.append(f"  #{i}: missing 'name'")

        # Check name uniqueness
        if name and name in names:
            errors.append(f"  #{i} ({name}): duplicate name/key")
        names.append(name)

        # Check URL presence
        if not url:
            errors.append(f"  #{i} ({name}): empty URL")
            continue

        # Check malformed URL
        parsed = urlparse(url)
        if not parsed.scheme or not parsed.netloc:
            errors.append(f"  #{i} ({name}): malformed URL — {url}")

        # Check URL uniqueness
        if url in urls:
            errors.append(f"  #{i} ({name}): duplicate URL")
        urls.append(url)

        # Check type
        src_type = src.get("type", "")
        if src_type not in ("m3u", "txt"):
            errors.append(f"  #{i} ({name}): unknown type '{src_type}' (expected m3u or txt)")

    if errors:
        print("❌ 验证失败:")
        for e in errors:
            print(e)
        sys.exit(1)
    else:
        print(f"✅ 验证通过: {len(sources)} 个源, 全部合法")


def cmd_list() -> None:
    """List all sources with their status."""
    sources = _get_sources()
    if not sources:
        print("(空)")
        return

    print(f"{'#':>3}  {'名称':<30} {'类型':<6} {'启用':<5} URL")
    print("-" * 90)
    for i, src in enumerate(sources, start=1):
        name = src.get("name", "?")
        url = src.get("url", "")
        src_type = src.get("type", "?")
        enabled = "✓" if src.get("enabled", True) else "✗"
        # Truncate URL for display
        url_display = url if len(url) < 60 else url[:57] + "..."
        print(f"{i:>3}  {name:<30} {src_type:<6} {enabled:<5} {url_display}")


def cmd_disabled() -> None:
    """List disabled sources."""
    sources = _get_sources()
    disabled = [s for s in sources if not s.get("enabled", True)]
    if not disabled:
        print("(无禁用源)")
        return
    print(f"{'#':>3}  {'名称':<30} {'类型':<6} URL")
    print("-" * 90)
    for i, src in enumerate(disabled, start=1):
        name = src.get("name", "?")
        url = src.get("url", "")
        src_type = src.get("type", "?")
        url_display = url if len(url) < 60 else url[:57] + "..."
        print(f"{i:>3}  {name:<30} {src_type:<6} {url_display}")


def main() -> None:
    if len(sys.argv) < 2:
        print("用法: python scripts/manage_sources.py <validate|list|disabled>")
        sys.exit(1)

    cmd = sys.argv[1]
    if cmd == "validate":
        cmd_validate()
    elif cmd == "list":
        cmd_list()
    elif cmd == "disabled":
        cmd_disabled()
    else:
        print(f"未知子命令: {cmd}")
        print("支持: validate, list, disabled")
        sys.exit(1)


if __name__ == "__main__":
    main()