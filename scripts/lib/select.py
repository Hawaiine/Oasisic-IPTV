"""选优：源 priority → 区域 → 频道级偏好 → 名称稳定性；全局 URL 去重；rtp 降权；目录制分流。"""

from __future__ import annotations

import logging
import re
from collections import Counter, defaultdict
from typing import Any

from .categories import RADIO_KEY, group_title, iter_main_order

logger = logging.getLogger(__name__)

REGION_RANK = {
    "cn": 0,
    "hk_tw": 1,
    "hotel": 2,
    "overseas": 3,
    "radio": 4,
}

DEFAULT_CHANNEL_PRIORITY = 50  # 频道表未写 priority 时的默认值（越小越优先）

# 时效性签名参数：URL query 带这些大概率会过期（分钟~小时级），选优时降权
# 只匹配 ?param= / &param= 位置，避免误伤域名或路径中的同名子串
_SIGNED_URL_RE = re.compile(
    r"[?&](?:auth_key|accountinfo|GuardEncType|SecurityKey|"
    r"timestamp|expires?|token|signed|sign|sig|st)=",
    re.IGNORECASE,
)


def _is_signed(url: str) -> bool:
    """带时效签名参数的 URL 视为不稳定（如北京移动 accountinfo、央视 auth_key）。"""
    return bool(_SIGNED_URL_RE.search(url or ""))


def _sort_key(entry: dict[str, Any]) -> tuple:
    url = entry.get("url") or ""
    rtp = 1 if url.startswith("rtp://") else 0
    # 时效签名降权：介于 rtp 与 region 之间，优先无签名稳定链接
    signed = 1 if _is_signed(url) else 0
    region = entry.get("source_region") or "overseas"
    # 频道级 preferred_region：命中则该源的区域排名视为最优先（cn 同级）
    pref = entry.get("preferred_region") or ""
    if pref and region == pref:
        region_rank = 0
    else:
        region_rank = REGION_RANK.get(region, 9)
    # 频道级 priority 优先于源 priority；默认 50 时行为与旧版一致
    channel_prio = int(entry.get("channel_priority") or DEFAULT_CHANNEL_PRIORITY)
    priority = int(entry.get("source_priority") or 100)
    matched = 0 if entry.get("matched") else 1
    # 名称稳定性：已匹配标准表优先
    name_len = len(entry.get("cleaned_name") or entry.get("name") or "")
    return (rtp, signed, region_rank, channel_prio, priority, matched, name_len)


def _dedup_urls(
    entries: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], int]:
    """全局 URL 去重：非 radio 优先保留。返回 (去重后, 被去重条数)。"""
    best: dict[str, dict[str, Any]] = {}
    order: list[str] = []
    dropped = 0
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
            dropped += 1
            continue
        if not old_radio and new_radio:
            dropped += 1
            continue
        if _sort_key(e) < _sort_key(old):
            best[url] = e
            dropped += 1
        else:
            dropped += 1
    return [best[u] for u in order if u in best], dropped


def select_best(
    entries: list[dict[str, Any]],
    *,
    max_keep: int = 1,
) -> list[dict[str, Any]]:
    """按 display/standard 名保留 max_keep 条，先全局 URL 去重。"""
    entries, dropped = _dedup_urls(entries)
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

    _log_select_stats(entries, dropped, selected, max_keep)
    return selected


def _log_select_stats(
    deduped: list[dict[str, Any]],
    dropped: int,
    selected: list[dict[str, Any]],
    max_keep: int,
) -> None:
    rtp_n = sum(1 for e in deduped if (e.get("url") or "").startswith("rtp://"))
    by_cat: Counter[str] = Counter(e.get("category") or "other" for e in selected)
    cat_str = " ".join(f"{c}={n}" for c, n in sorted(by_cat.items()))
    logger.info(
        "[select] rtp=%d url_dropped=%d selected=%d max_keep=%d cats: %s",
        rtp_n,
        dropped,
        len(selected),
        max_keep,
        cat_str or "-",
    )


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
    logger.info(
        "[select] split catalog=%d more=%d radio=%d",
        len(catalog),
        len(more),
        len(radio),
    )
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
