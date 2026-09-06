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


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.parse_args()
    root = project_root()
    errors: list[str] = []
    check_zero_orphan(root, errors)

    live = check_m3u(root / "output" / "live.m3u", max_keep=1, require_nonempty=True, errors=errors)
    check_m3u(root / "output" / "live_more.m3u", max_keep=1, require_nonempty=False, errors=errors)
    check_m3u(root / "output" / "live_radio.m3u", max_keep=1, require_nonempty=False, errors=errors)
    backup_path = root / "output" / "live_backup.m3u"
    if backup_path.exists():
        check_m3u(backup_path, max_keep=3, require_nonempty=False, errors=errors)

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
        fail("check_result.json 不存在", errors)
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
            f"ratio={data.get('ratio')}"
        )

    # 电台不得混入主列表
    radio_in_main = sum(1 for e in live if e.get("group") == group_title("radio"))
    if radio_in_main:
        fail(f"电台混入 live.m3u: {radio_in_main}", errors)
    else:
        ok("radio_in_main=False")

    # tvg_id 对账：只警告，不失败
    _warn_epg_tvg_ids(root, live)

    if errors:
        print(f"\n❌ 校验失败 {len(errors)} 项")
        sys.exit(1)
    print("\n✅ verify_outputs 全部通过")


def _warn_epg_tvg_ids(root: Path, live: list[dict]) -> None:
    channels = load_json(root / "data" / "channels.json")
    table_ids = {str(ch.get("tvg_id") or "").strip() for ch in channels if ch.get("tvg_id")}
    live_ids = {str(e.get("tvg_id") or "").strip() for e in live if e.get("tvg_id")}
    guide = root / "output" / "guide.xml"
    if not guide.exists():
        print("⚠ EPG 对账：output/guide.xml 不存在（fetch_epg 未跑或失败）")
        return
    try:
        tree = ET.parse(guide)
        epg_ids = {ch.get("id") or "" for ch in tree.findall("channel")}
    except ET.ParseError as exc:
        print(f"⚠ EPG 对账：guide.xml 无法解析 ({exc})")
        return
    missing_table = sorted(table_ids - epg_ids)
    missing_live = sorted(live_ids - epg_ids)
    if missing_table:
        print(f"⚠ 标准表 {len(missing_table)} 个 tvg_id 不在 guide.xml: {missing_table[:12]}")
    if missing_live:
        print(f"⚠ 主列表 {len(missing_live)} 个 tvg_id 不在 guide.xml: {missing_live[:12]}")
    if not missing_table and not missing_live:
        ok(f"EPG 对账：guide.xml 覆盖标准表 {len(table_ids)} / 主列表 {len(live_ids)}")


if __name__ == "__main__":
    main()
