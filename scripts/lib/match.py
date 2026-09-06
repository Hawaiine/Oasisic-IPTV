"""频道匹配：精确 → 别名 → 有限模糊。命中标准表才进目录制主列表。"""

from __future__ import annotations

import logging
import re
from collections import Counter
from typing import Any

from .clean import clean_channel_name

logger = logging.getLogger(__name__)


def _fold(s: str) -> str:
    return re.sub(r"[\s\-—_]+", "", (s or "")).lower()


class ChannelMatcher:
    def __init__(
        self,
        channels: list[dict[str, Any]],
        aliases: dict[str, list[str]] | list[dict[str, Any]],
    ) -> None:
        self.channels = channels
        self.by_standard: dict[str, dict[str, Any]] = {}
        self.by_display: dict[str, dict[str, Any]] = {}
        self.by_fold: dict[str, dict[str, Any]] = {}
        self.alias_to_standard: dict[str, str] = {}
        # 每次 attach_match 前重置；记录命中路径用于可观测性统计
        self.stats: Counter[str] = Counter()

        for ch in channels:
            std = ch.get("standard_name") or ""
            disp = ch.get("display_name") or std
            if not std:
                continue
            self.by_standard[std] = ch
            self.by_display[disp] = ch
            self.by_fold[_fold(std)] = ch
            self.by_fold[_fold(disp)] = ch

        # aliases.json 支持两种形态：
        # 1) { "湖南卫视": ["湖南", "Hunan TV"] }  key 必须是 standard_name
        # 2) [ {"alias": "...", "standard_name": "..."} ]
        if isinstance(aliases, dict):
            for std, als in aliases.items():
                if std not in self.by_standard:
                    # orphan 在校验阶段拦截；匹配时忽略
                    continue
                for a in als or []:
                    self.alias_to_standard[a] = std
                    self.by_fold[_fold(a)] = self.by_standard[std]
        else:
            for item in aliases:
                std = item.get("standard_name") or ""
                a = item.get("alias") or ""
                if std in self.by_standard and a:
                    self.alias_to_standard[a] = std
                    self.by_fold[_fold(a)] = self.by_standard[std]

        self.standard_names = set(self.by_standard)

    def match(self, raw_name: str) -> dict[str, Any] | None:
        cleaned = clean_channel_name(raw_name)
        if not cleaned:
            return None
        if cleaned in self.by_standard:
            self.stats["exact"] += 1
            return self.by_standard[cleaned]
        if cleaned in self.by_display:
            self.stats["exact"] += 1
            return self.by_display[cleaned]
        if cleaned in self.alias_to_standard:
            self.stats["alias"] += 1
            return self.by_standard[self.alias_to_standard[cleaned]]
        folded = _fold(cleaned)
        if folded in self.by_fold:
            self.stats["fuzzy"] += 1
            return self.by_fold[folded]
        self.stats["miss"] += 1
        return None


def attach_match(
    entries: list[dict[str, Any]],
    matcher: ChannelMatcher,
) -> list[dict[str, Any]]:
    """给每条记录打上 matched / standard_name / display_name / category / tvg_*。

    同时输出 [match] 命中统计（总频道数、精确/别名/模糊/未命中、命中率）。
    """
    matcher.stats = Counter()
    out: list[dict[str, Any]] = []
    for e in entries:
        raw = e.get("name") or ""
        cleaned = clean_channel_name(raw)
        hit = matcher.match(raw)
        rec = dict(e)
        rec["cleaned_name"] = cleaned
        if hit:
            rec["matched"] = True
            rec["standard_name"] = hit["standard_name"]
            rec["display_name"] = hit.get("display_name") or hit["standard_name"]
            rec["category"] = hit.get("category") or rec.get("category") or "other"
            rec["tvg_id"] = hit.get("tvg_id") or rec.get("tvg_id") or ""
            rec["tvg_logo"] = rec.get("tvg_logo") or hit.get("tvg_logo") or ""
            # 频道级选优提示（可选字段，旧数据缺失时保持默认）
            if "priority" in hit:
                rec["channel_priority"] = hit["priority"]
            if "preferred_region" in hit:
                rec["preferred_region"] = hit["preferred_region"]
        else:
            rec["matched"] = False
            rec["standard_name"] = cleaned
            rec["display_name"] = cleaned
        out.append(rec)

    _log_match_stats(matcher, len(entries))
    return out


def _log_match_stats(matcher: ChannelMatcher, total: int) -> None:
    st = matcher.stats
    hit_n = st.get("exact", 0) + st.get("alias", 0) + st.get("fuzzy", 0)
    miss_n = st.get("miss", 0)
    rate = hit_n / total if total else 0.0
    logger.info(
        "[match] total=%d exact=%d alias=%d fuzzy=%d miss=%d hit_rate=%.1f%%",
        total,
        st.get("exact", 0),
        st.get("alias", 0),
        st.get("fuzzy", 0),
        miss_n,
        rate * 100,
    )
