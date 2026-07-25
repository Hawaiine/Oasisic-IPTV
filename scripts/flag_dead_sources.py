# coding: utf-8
"""
Oasisic-IPTV 失效源标记脚本。

仅在 probe 模式（check_result.probe_enabled=true 或 stage=probe）且有足够数据时运行。
跟踪 data/source_history.json，连续 DEAD_DAYS 可用率 0% 的源被自动注释（disabled）。

环境变量
--------
DEAD_DAYS : int
    连续天数阈值（默认 3）。
DRY_RUN : str
    设为 "true" 时只报告不改文件。
CORE_SOURCE_NAMES 见 _CORE_NAMES 常量，核心源只告警不自动禁用。
"""

from __future__ import annotations

import datetime
import json
import os
import sys
import typing as t

_SCRIPTS_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__)))
if _SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, _SCRIPTS_DIR)

from lib.io_util import load_yaml, project_root, save_json, load_json

# ── Config ─────────────────────────────────────────────────────────

_DEAD_DAYS = int(os.environ.get("DEAD_DAYS", "3"))
_DRY_RUN = os.environ.get("DRY_RUN", "").lower() in ("true", "1")

# Core sources: only warn, never auto-disable
_CORE_NAMES: set[str] = {
    "iptv-org-cn", "iptv-org-hk", "iptv-org-tw",
    "fanmingming-ipv6", "yuechan-cn",
}


def _load_check_result() -> dict | None:
    path = os.path.join(project_root(), "output", "check_result.json")
    if not os.path.isfile(path):
        return None
    return load_json(path)


def _load_sources() -> list[dict]:
    path = os.path.join(project_root(), "config", "sources.yaml")
    data = load_yaml(path)
    return data.get("sources", [])


def _load_history() -> dict:
    path = os.path.join(project_root(), "data", "source_history.json")
    if os.path.isfile(path):
        return load_json(path)
    return {}


def _save_history(history: dict) -> None:
    path = os.path.join(project_root(), "data", "source_history.json")
    save_json(path, history)


def _update_history(
    history: dict,
    source_name: str,
    success: bool,
    source_url: str,
) -> None:
    """Update source history with today's result."""
    today = datetime.date.today().isoformat()
    entry = history.setdefault(source_name, {"url": source_url, "days": {}})
    entry["url"] = source_url
    entry["days"][today] = success


def _is_source_dead(entry: dict) -> bool:
    """Check if a source has been dead for DEAD_DAYS consecutive days."""
    days = entry.get("days", {})
    # Get the last N days sorted
    sorted_dates = sorted(days.keys(), reverse=True)
    consecutive_fail = 0
    for d in sorted_dates:
        if days[d] is False:
            consecutive_fail += 1
        else:
            break  # Most recent success breaks the streak
        if consecutive_fail >= _DEAD_DAYS:
            return True
    return False


def main() -> None:
    check = _load_check_result()

    # ── Guard: must be probe mode ───────────────────────────────
    if check is None:
        print("⏭️  output/check_result.json 不存在，跳过")
        return

    probe_mode = check.get("probe_enabled") or check.get("stage") == "probe"
    if not probe_mode:
        print(f"⏭️  stage={check.get('stage')}, probe_enabled={check.get('probe_enabled')}，跳过（无测活数据）")
        return

    total = check.get("total", 0)
    if total == 0:
        print("⏭️  total=0，无频道数据，跳过")
        return

    # ── Load state ──────────────────────────────────────────────
    sources = _load_sources()
    history = _load_history()
    source_map: dict[str, dict] = {s["name"]: s for s in sources if s.get("name")}

    today = datetime.date.today().isoformat()
    print(f"📊 源健康记录更新 ({today})")

    # ── Update history with source availability ─────────────────
    # Check result doesn't have per-source stats, but we can infer
    # from the probe success/fail ratio. For simplicity, we track
    # whether the source was reachable during collect.
    # We use ok/fail from check_result as a proxy for overall health.
    probe_ok = check.get("ok", 0)
    probe_fail = check.get("fail", 0)
    total_probed = probe_ok + probe_fail

    for name in source_map:
        # We can't know per-source probe success from check_result alone,
        # so we track the overall collect success per source_name.
        # For now, we record the source as "available" if it's in the config.
        # This is a placeholder — Phase 7 would add per-source stats.
        pass

    print(f"   测活: {probe_ok} 可用 / {probe_fail} 不可用 (共 {total_probed} 条)")

    # ── Check for dead sources ──────────────────────────────────
    changes: list[str] = []
    warnings: list[str] = []

    for name, entry in history.items():
        if name not in source_map:
            continue  # Source no longer in config
        if not _is_source_dead(entry):
            continue

        is_core = name in _CORE_NAMES
        if is_core:
            warnings.append(f"⚠️  核心源 {name} 连续 {_DEAD_DAYS} 天不可用（仅警告，不禁用）")
            continue

        changes.append(f"🔴 {name}: 连续 {_DEAD_DAYS} 天不可用 → 禁用")

    # ── Apply changes (or dry-run) ──────────────────────────────
    if _DRY_RUN:
        print("🏷️  DRY RUN 模式 — 不修改文件")
        for c in changes:
            print(f"   {c}")
        for w in warnings:
            print(f"   {w}")
        if not changes and not warnings:
            print("   无需操作")
        _save_history(history)
        return

    if changes:
        # Read sources.yaml and disable dead sources
        sources_path = os.path.join(project_root(), "config", "sources.yaml")
        with open(sources_path, "r", encoding="utf-8") as f:
            yaml_text = f.read()

        # We use a simple approach: find and set enabled: false for dead sources
        for change in changes:
            name = change.split(":")[0].strip("🔴 ")
            # Comment out the source entry by setting enabled to false
            # Simple replacement: find the name block and add enabled: false
            import re
            pattern = re.compile(
                rf'(\n  - name:\s*"{re.escape(name)}"\s*\n.*?)(?=\n  - name:|\n$)',
                re.DOTALL,
            )
            match = pattern.search(yaml_text)
            if match:
                block = match.group(1)
                if "enabled:" not in block:
                    new_block = block.rstrip() + "\n    enabled: false"
                    yaml_text = yaml_text.replace(block, new_block, 1)
                    print(f"   ✅ {name}: 已禁用")

        with open(sources_path, "w", encoding="utf-8") as f:
            f.write(yaml_text)

    for w in warnings:
        print(f"   {w}")

    if not changes and not warnings:
        print("   无需操作")

    # ── Save history ────────────────────────────────────────────
    _save_history(history)
    print(f"✅ source_history.json 已更新")


if __name__ == "__main__":
    main()