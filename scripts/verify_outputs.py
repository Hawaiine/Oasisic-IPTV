#!/usr/bin/env python3
"""输出校验：主列表一台一链、分类完整、空文件、zero-orphan。"""

from __future__ import annotations

import argparse
import json
import sys
import xml.etree.ElementTree as ET
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from lib.categories import CATEGORIES, group_title, iter_main_order  # noqa: E402
from lib.health import index_age_days  # noqa: E402
from lib.io_util import load_json, project_root  # noqa: E402
from lib.m3u import parse_m3u  # noqa: E402

ALLOWED_GROUPS = {info[0] for info in CATEGORIES.values()}
EXPECTED_URL_TVG = 'url-tvg="https://live.fanmingming.com/e.xml"'


def fail(msg: str, errors: list[str]) -> None:
    errors.append(msg)
    print(f"❌ {msg}")


def ok(msg: str) -> None:
    print(f"✅ {msg}")


def check_zero_orphan(root: Path, errors: list[str]) -> None:
    channels = load_json(root / "data" / "channels.json")
    aliases = load_json(root / "data" / "aliases.json")
    std = {ch["standard_name"] for ch in channels}
    orphans: list[str] = []
    if isinstance(aliases, dict):
        for key, vals in aliases.items():
            if key not in std:
                orphans.append(key)
            for _v in vals or []:
                pass
    else:
        for item in aliases:
            if item.get("standard_name") not in std:
                orphans.append(str(item))
    if orphans:
        fail(f"aliases orphan {len(orphans)}: {orphans[:8]}", errors)
    else:
        ok("zero-orphan")


def check_entries_quality(
    path: Path,
    entries: list[dict],
    errors: list[str],
    *,
    allow_other: bool = False,
    label: str = "",
) -> None:
    """逐文件检查 group-title 标准化与「属性原文混入频道名」。"""
    tag = label or path.name
    bad_groups: list[str] = []
    leaked = 0
    other = 0
    for e in entries:
        g = e.get("group") or ""
        if g not in ALLOWED_GROUPS:
            bad_groups.append(g or "<空>")
        if g == "其他":
            other += 1
        if '="' in (e.get("name") or ""):
            leaked += 1
    if bad_groups:
        uniq = sorted(set(bad_groups))
        fail(f"{tag} 非标准 group-title {len(bad_groups)} 条: {uniq[:6]}", errors)
    elif entries:
        ok(f"{tag} group-title 全部标准化")
    if leaked:
        fail(f"{tag} 有 {leaked} 条频道名混入属性原文（解析畸形）", errors)
    elif entries:
        ok(f"{tag} 频道名无属性泄漏")
    if not allow_other and other:
        fail(f"{tag} 其他类 {other} 条（应只出现在 live_more）", errors)


def check_m3u(path: Path, *, max_keep: int, require_nonempty: bool, errors: list[str]) -> list[dict]:
    if not path.exists():
        fail(f"{path.name} 不存在", errors)
        return []
    text = path.read_text(encoding="utf-8")
    first = next((ln.strip() for ln in text.splitlines() if ln.strip()), "")
    if not first.startswith("#EXTM3U"):
        fail(f"{path.name} 不是 #EXTM3U", errors)
    elif EXPECTED_URL_TVG not in first:
        fail(f"{path.name} 缺少 {EXPECTED_URL_TVG}", errors)
    entries = parse_m3u(text)
    if require_nonempty and not entries:
        fail(f"{path.name} 为空", errors)
        return entries
    names = [e.get("name") or "" for e in entries]
    urls = [e.get("url") or "" for e in entries]
    name_c = Counter(names)
    url_c = Counter(urls)
    mx = max(name_c.values()) if name_c else 0
    if mx > max_keep:
        over = {k: v for k, v in name_c.items() if v > max_keep}
        fail(f"{path.name} max/名={mx} > {max_keep}: {list(over)[:5]}", errors)
    else:
        ok(f"{path.name}: {len(entries)} 条, 唯一名 {len(name_c)}, 唯一URL {len(url_c)}, max/名={mx}")
    return entries


def check_txt(root: Path, errors: list[str]) -> None:
    """TXT 版（TVBox/DIYP）与 M3U 同口径：分组必须是中文 group-title，条目数需对齐。"""
    pairs = (
        ("live.txt", "live.m3u", 1.0),
        ("live_lite.txt", "live.m3u", 0.0),   # 精简版只做存在性 + 分组检查
        ("live_more.txt", "live_more.m3u", 1.0),
        ("live_radio.txt", "live_radio.m3u", 1.0),
    )
    expected_groups = {info[0] for info in CATEGORIES.values()}
    for txt_name, m3u_name, ratio_floor in pairs:
        txt_path = root / "output" / txt_name
        if not txt_path.exists():
            fail(f"{txt_name} 不存在（settings.write_txt 应为 true）", errors)
            continue
        lines = [ln.strip() for ln in txt_path.read_text(encoding="utf-8").splitlines() if ln.strip()]
        groups = [ln.rsplit(",", 1)[0] for ln in lines if ln.endswith("#genre#")]
        bad = [g for g in groups if g not in expected_groups]
        if bad:
            fail(f"{txt_name} 非标准分组 {sorted(set(bad))[:5]}", errors)
            continue
        items = [ln for ln in lines if not ln.endswith("#genre#") and not ln.startswith("#")]
        for ln in items:
            if "," not in ln:
                fail(f"{txt_name} 存在无逗号行: {ln[:40]}", errors)
                break
        m3u_path = root / "output" / m3u_name
        m3u_entries = parse_m3u(m3u_path.read_text(encoding="utf-8")) if m3u_path.exists() else []
        if ratio_floor and m3u_entries and len(items) < int(len(m3u_entries) * ratio_floor):
            fail(f"{txt_name} 条数 {len(items)} 少于 {m3u_name} 的 {len(m3u_entries)}", errors)
        else:
            ok(f"{txt_name}: {len(items)} 条, 分组 {len(set(groups))} 个")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.parse_args()
    root = project_root()
    errors: list[str] = []
    check_zero_orphan(root, errors)

    live = check_m3u(root / "output" / "live.m3u", max_keep=1, require_nonempty=True, errors=errors)
    more = check_m3u(root / "output" / "live_more.m3u", max_keep=1, require_nonempty=False, errors=errors)
    radio = check_m3u(root / "output" / "live_radio.m3u", max_keep=1, require_nonempty=False, errors=errors)
    backup: list[dict] = []
    backup_path = root / "output" / "live_backup.m3u"
    if backup_path.exists():
        backup = check_m3u(backup_path, max_keep=3, require_nonempty=False, errors=errors)

    # 逐文件质量口径（旧版只看 live.m3u，live_more/live_radio 的分组与脏名无人管）
    for path, entries, allow_other in (
        (root / "output" / "live.m3u", live, False),
        (root / "output" / "live_more.m3u", more, True),
        (root / "output" / "live_radio.m3u", radio, False),
        (backup_path, backup, False),
    ):
        if entries or path.exists():
            check_entries_quality(path, entries, errors, allow_other=allow_other)

    check_txt(root, errors)

    # 探活分列（可选产物，存在即校验；属「问题清单」，同频道最多 3 条）
    for col in ("live_ipv6.m3u", "live_cmcc.m3u", "live_signed.m3u"):
        col_path = root / "output" / col
        if col_path.exists():
            check_m3u(col_path, max_keep=3, require_nonempty=False, errors=errors)
    check_health(root, errors)

    other = 0
    bad_group = 0
    for e in live:
        g = e.get("group") or ""
        if g not in ALLOWED_GROUPS:
            bad_group += 1
        if g in {"其他", ""}:
            other += 1
    if live:
        pct = other / len(live)
        if pct > 0:
            fail(f"live.m3u other 占比 {pct:.1%}（目录制主列表应为 0）", errors)
        else:
            ok("live.m3u other%=0")
    if bad_group:
        fail(f"live.m3u 非标准 group-title {bad_group} 条", errors)
    else:
        ok("group-title 全部标准化")

    # 分类文件存在
    for cat in iter_main_order():
        suffix = CATEGORIES[cat][1]
        p = root / "output" / f"live_{suffix}.m3u"
        if not p.exists():
            fail(f"缺少 live_{suffix}.m3u", errors)

    cr = root / "output" / "check_result.json"
    if not cr.exists():
        # 干净克隆里该文件被 .gitignore 忽略（CI 中 collect 刚写完必然存在）→ 仅提示
        print("⚠ check_result.json 不存在（干净克隆属正常；CI 中由 collect 生成）")
    else:
        data = json.loads(cr.read_text(encoding="utf-8"))
        if data.get("schema_version") != 1:
            fail("check_result schema_version != 1", errors)
        if data.get("stage") != "collect":
            fail(f"check_result stage={data.get('stage')}", errors)
        if data.get("timezone") != "Asia/Shanghai":
            fail("timezone 应为 Asia/Shanghai", errors)
        ok(
            f"check_result catalog={data.get('catalog')} more={data.get('more')} "
            f"ratio={data.get('ratio')} more_dropped={data.get('more_dropped')}"
        )

    # 电台不得混入主列表
    radio_in_main = sum(1 for e in live if e.get("group") == group_title("radio"))
    if radio_in_main:
        fail(f"电台混入 live.m3u: {radio_in_main}", errors)
    else:
        ok("radio_in_main=False")

    # EPG 覆盖率硬检查（阈值 settings.epg_min_coverage）
    check_epg_coverage(root, live, errors)

    if errors:
        print(f"\n❌ 校验失败 {len(errors)} 项")
        sys.exit(1)
    print("\n✅ verify_outputs 全部通过")


def check_health(root: Path, errors: list[str]) -> None:
    """探活产物校验（存在才校验；CI 无探活时为跳过）。"""
    path = root / "output" / "health.json"
    if not path.exists():
        print("ℹ health.json 不存在（未跑探活）→ 选优按旧口径")
        return
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        fail(f"health.json 无法解析: {exc}", errors)
        return
    if data.get("schema_version") != 1:
        fail(f"health schema_version={data.get('schema_version')}", errors)
    if data.get("stage") != "probe":
        fail(f"health stage={data.get('stage')}", errors)
    if data.get("timezone") != "Asia/Shanghai":
        fail("health timezone 应为 Asia/Shanghai", errors)
    urls = data.get("urls")
    if not isinstance(urls, dict) or not urls:
        fail("health.urls 为空", errors)
        return
    egress = (data.get("egress") or {}).get("label") or "unknown"
    age = index_age_days(data)
    max_age = 7
    probe_cfg = root / "config" / "probe.yaml"
    if probe_cfg.exists():
        try:
            import yaml

            max_age = int((yaml.safe_load(probe_cfg.read_text(encoding="utf-8")) or {}).get("max_age_days") or 7)
        except Exception:  # noqa: BLE001
            max_age = 7
    ok(
        f"health.json: {len(urls)} 条, 出口 {egress}, 已过 {age} 天, 分级 {data.get('counts')}"
    )
    if age is not None and age > max_age:
        print(f"⚠ health.json 已过 {age} 天 > {max_age} 天，选优将回退旧口径（建议重跑 scripts/probe.py）")


def check_epg_coverage(root: Path, live: list[dict], errors: list[str]) -> None:
    """EPG 覆盖率硬检查：低于 settings.epg_min_coverage 则失败。

    覆盖率口径 = 标准表里有 guide.xml 节目单的频道数 / 标准表总数，
    期望 id 取 `epg_id or tvg_id`。
    """
    channels = load_json(root / "data" / "channels.json")
    total = len(channels)
    if not total:
        fail("channels.json 为空", errors)
        return

    def _expect_id(ch: dict) -> str:
        return str(ch.get("epg_id") or ch.get("tvg_id") or "").strip()

    guide = root / "output" / "guide.xml"
    if not guide.exists():
        print("⚠ EPG 覆盖率：output/guide.xml 不存在（fetch_epg 未跑或失败）")
        return
    try:
        tree = ET.parse(guide)
    except ET.ParseError as exc:
        fail(f"guide.xml 无法解析 ({exc})", errors)
        return
    epg_ids = {ch.get("id") or "" for ch in tree.findall("channel")}
    prog_ids = {
        p.get("channel") or "" for p in tree.findall("programme") if (p.get("channel") or "")
    }
    covered = [ch for ch in channels if _expect_id(ch) in prog_ids]
    ratio = len(covered) / total

    by_cat: dict[str, list[int]] = {}
    for ch in channels:
        got = 1 if _expect_id(ch) in prog_ids else 0
        t, g = by_cat.get(ch.get("category") or "other", [0, 0])
        by_cat[ch.get("category") or "other"] = [t + 1, g + got]
    detail = " ".join(f"{k}={v[1]}/{v[0]}" for k, v in sorted(by_cat.items()))

    try:
        import yaml

        settings = yaml.safe_load((root / "config" / "settings.yaml").read_text(encoding="utf-8")) or {}
    except Exception:  # noqa: BLE001
        settings = {}
    threshold = float(settings.get("epg_min_coverage") or 0.6)

    if ratio < threshold:
        fail(
            f"EPG 覆盖率 {len(covered)}/{total} = {ratio:.1%} < 阈值 {threshold:.0%}（{detail}）",
            errors,
        )
    else:
        ok(f"EPG 覆盖率 {len(covered)}/{total} = {ratio:.1%}（阈值 {threshold:.0%}）| {detail}")

    missing_channels = [ch for ch in channels if _expect_id(ch) not in prog_ids]
    miss_file = root / "data" / "epg_missing.txt"
    if missing_channels and not miss_file.exists():
        fail(f"有 {len(missing_channels)} 个频道无 EPG，但缺少 data/epg_missing.txt", errors)
    elif missing_channels:
        ok(f"缺口清单 data/epg_missing.txt 存在（{len(missing_channels)} 个未覆盖）")

    # 主列表 tvg-id 与 guide.xml 对账（只提示，不失败——无 EPG 的频道本来就对不上）
    live_ids = {str(e.get("tvg_id") or "").strip() for e in live if e.get("tvg_id")}
    missing_live = sorted(live_ids - epg_ids)
    if missing_live:
        print(f"ℹ 主列表 {len(missing_live)} 个 id 不在 guide.xml（预期：无 EPG 的频道）: {missing_live[:8]}")


if __name__ == "__main__":
    main()
