"""频道匹配：精确 → 别名 → 有限模糊。命中标准表才进目录制主列表。"""

from __future__ import annotations

import re
from typing import Any

from .clean import clean_channel_name


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
            return self.by_standard[cleaned]
        if cleaned in self.by_display:
            return self.by_display[cleaned]
        if cleaned in self.alias_to_standard:
            return self.by_standard[self.alias_to_standard[cleaned]]
        folded = _fold(cleaned)
        if folded in self.by_fold:
            return self.by_fold[folded]
        return None


def attach_match(
    entries: list[dict[str, Any]],
    matcher: ChannelMatcher,
) -> list[dict[str, Any]]:
    """给每条记录打上 matched / standard_name / display_name / category / tvg_*。"""
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
        else:
            rec["matched"] = False
            rec["standard_name"] = cleaned
            rec["display_name"] = cleaned
        out.append(rec)
    return out
