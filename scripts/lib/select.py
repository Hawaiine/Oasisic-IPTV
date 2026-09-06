"""选优：源 priority → 区域 → 名称稳定性；全局 URL 去重；rtp 降权；目录制分流。"""

from __future__ import annotations

import re
from collections import defaultdict
from typing import Any

from .categories import RADIO_KEY, group_title, iter_main_order

REGION_RANK = {
    "cn": 0,
    "hk_tw": 1,
    "hotel": 2,
    "overseas": 3,
    "radio": 4,
}


def _sort_key(entry: dict[str, Any]) -> tuple:
    url = entry.get("url") or ""
    rtp = 1 if url.startswith("rtp://") else 0
    region = entry.get("source_region") or "overseas"
    region_rank = REGION_RANK.get(region, 9)
    priority = int(entry.get("source_priority") or 100)
    matched = 0 if entry.get("matched") else 1
    # 名称稳定性：已匹配标准表优先
    name_len = len(entry.get("cleaned_name") or entry.get("name") or "")
    return (rtp, region_rank, priority, matched, name_len)


def _dedup_urls(entries: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """全局 URL 去重：非 radio 优先保留。"""
    best: dict[str, dict[str, Any]] = {}
    order: list[str] = []
    for e in entries:
        url = e.get("url") or ""
        if not url:
            continue
        if url not in best:
            best[url] = e
            order.append(url)
            continue
        old = best[url]
        old_radio = (old.get("category") == RADIO_KEY)
        new_radio = (e.get("category") == RADIO_KEY)
        if old_radio and not new_radio:
            best[url] = e
            continue
        if not old_radio and new_radio:
            continue
        if _sort_key(e) < _sort_key(old):
            best[url] = e
    return [best[u] for u in order if u in best]


def select_best(
    entries: list[dict[str, Any]],
    *,
    max_keep: int = 1,
) -> list[dict[str, Any]]:
    """按 display/standard 名保留 max_keep 条，先全局 URL 去重。"""
    entries = _dedup_urls(entries)
    groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    radio: list[dict[str, Any]] = []
    for e in entries:
        if e.get("category") == RADIO_KEY:
            radio.append(e)
            continue
        key = e.get("standard_name") or e.get("display_name") or e.get("cleaned_name") or e.get("name") or ""
        groups[key].append(e)

    selected: list[dict[str, Any]] = []
    for _name, items in groups.items():
        items.sort(key=_sort_key)
        selected.extend(items[: max(1, max_keep)])

    radio_groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for e in radio:
        key = e.get("standard_name") or e.get("display_name") or e.get("name") or ""
        radio_groups[key].append(e)
    for items in radio_groups.values():
        items.sort(key=_sort_key)
        selected.extend(items[: max(1, max_keep)])
    return selected


def split_catalog_more(
    entries: list[dict[str, Any]],
    *,
    more_max_channels: int = 3000,
    main_include_overseas: bool = False,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    """返回 (catalog, more, radio)。catalog 仅标准表命中。"""
    catalog: list[dict[str, Any]] = []
    more: list[dict[str, Any]] = []
    radio: list[dict[str, Any]] = []
    for e in entries:
        cat = e.get("category") or "other"
        if cat == RADIO_KEY:
            radio.append(e)
            continue
        if not main_include_overseas and cat == "overseas":
            more.append(e)
            continue
        if e.get("matched"):
            catalog.append(e)
        else:
            more.append(e)
    if more_max_channels > 0 and len(more) > more_max_channels:
        more = more[:more_max_channels]
    return catalog, more, radio


def _name_sort(entry: dict[str, Any]) -> tuple:
    """央视按台号排序（CCTV-1…17，再 4K/8K），其余按显示名。"""
    name = entry.get("display_name") or entry.get("name") or ""
    if name.startswith("CCTV-4K"):
        return (0, 100.0, name)
    if name.startswith("CCTV-8K"):
        return (0, 101.0, name)
    m = re.match(r"CCTV-(\d+)(\+)?", name)
    if m:
        n = int(m.group(1))
        if m.group(2):
            n += 0.5
        return (0, n, name)
    return (1, 0.0, name)


def order_for_output(entries: list[dict[str, Any]]) -> list[dict[str, Any]]:
    buckets: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for e in entries:
        cat = e.get("category") or "other"
        e = dict(e)
        e["group_title"] = group_title(cat)
        buckets[cat].append(e)
    ordered: list[dict[str, Any]] = []
    for cat in iter_main_order():
        items = buckets.get(cat) or []
        items.sort(key=_name_sort)
        ordered.extend(items)
    return ordered
