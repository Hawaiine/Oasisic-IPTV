"""名称黑名单：过滤点播回看、购物、测试、引流等非直播噪声（config/exclude.yaml 配置）。"""

from __future__ import annotations

import re
from typing import Any

DEFAULT_PATTERNS: tuple[str, ...] = (
    r"\d{4}\s*年?春晚",           # 历年春晚回看（点播内容，不是直播频道）
    r"斗地主|棋牌|棋牌室|打牌",
    r"购物|商城|shopping",
    r"测试|试看|试用|test|demo|样本",
    r"加群|客服|代理|导航站|联系|威信|微信|QQ\s*群|telegram",
    r"成人|福利片|性感|深夜档",
    r"彩票|博彩|娱乐场|赌博",
    r"预告|片花|彩蛋|花絮",
    r"^\s*[\d\s+\-.、]+\s*$",     # 纯数字 / 纯符号名字
)

_CACHE: dict[str, re.Pattern[str]] = {}


def load_patterns(config: dict[str, Any] | None) -> list[str]:
    """从 exclude.yaml 读取 patterns；缺失时回落到内置默认。"""
    if isinstance(config, dict):
        pats = config.get("patterns")
        if isinstance(pats, list) and pats:
            return [str(p) for p in pats if str(p).strip()]
    return list(DEFAULT_PATTERNS)


def compile_patterns(patterns: list[str]) -> list[re.Pattern[str]]:
    out: list[re.Pattern[str]] = []
    for p in patterns:
        key = p.strip()
        if not key:
            continue
        if key not in _CACHE:
            try:
                _CACHE[key] = re.compile(key, re.IGNORECASE)
            except re.error:
                continue
        out.append(_CACHE[key])
    return out


def is_excluded(name: str, patterns: list[str]) -> bool:
    text = (name or "").strip()
    if not text:
        return True
    return any(p.search(text) for p in compile_patterns(patterns))


def filter_entries(
    entries: list[dict[str, Any]],
    patterns: list[str],
) -> tuple[list[dict[str, Any]], list[str]]:
    """返回 (保留条目, 被丢弃的名字列表)。"""
    kept: list[dict[str, Any]] = []
    dropped: list[str] = []
    for e in entries:
        name = e.get("name") or ""
        if is_excluded(name, patterns):
            dropped.append(name)
        else:
            kept.append(e)
    return kept, dropped