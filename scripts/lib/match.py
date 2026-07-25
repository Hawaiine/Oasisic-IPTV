# coding: utf-8
"""
Channel name matching against the standard channel table.

Uses ``data/channels.json`` (canonical list) and ``data/aliases.json``
(additional name variants) loaded at import time.

Functions
---------
match_channel(name, source="") -> dict | None
    Return the matching channel dict, or None.
"""

from __future__ import annotations

import os
import json
import typing as t

# ── Module-level state ─────────────────────────────────────────────

_channels: list[dict[str, t.Any]] = []
_aliases: dict[str, str] = {}

# Determine project root (two levels up from scripts/lib/)
_PROJECT_ROOT = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..")
)


def _load_tables() -> None:
    """Load channels.json and aliases.json into module globals."""
    global _channels, _aliases

    # Load channels
    ch_path = os.path.join(_PROJECT_ROOT, "data", "channels.json")
    if os.path.isfile(ch_path):
        with open(ch_path, "r", encoding="utf-8") as f:
            _channels = json.load(f)

    # Load aliases
    al_path = os.path.join(_PROJECT_ROOT, "data", "aliases.json")
    if os.path.isfile(al_path):
        with open(al_path, "r", encoding="utf-8") as f:
            _aliases = json.load(f)


# Auto-load on import
_load_tables()


def reload_tables() -> None:
    """Force reload of channels.json and aliases.json (useful in tests)."""
    _load_tables()


# ── Public API ─────────────────────────────────────────────────────


def match_channel(name: str, source: str = "") -> dict | None:
    """
    Match a channel name against the standard table.

    Strategy
    --------
    1. Direct match against ``standard_name`` in channels.
    2. Alias lookup in ``aliases.json``.
    3. Substring / fuzzy matching (future).

    Parameters
    ----------
    name : str
        Channel name to match (preferably cleaned).
    source : str
        Source identifier (for provenance tracking).

    Returns
    -------
    dict | None
        Matched channel entry from channels.json, or None.
    """
    name = name.strip()
    if not name:
        return None

    # 1. Direct match on standard_name
    for ch in _channels:
        if ch.get("standard_name", "").strip() == name:
            return dict(ch)

    # 2. Alias lookup
    canonical = _aliases.get(name)
    if canonical:
        for ch in _channels:
            if ch.get("standard_name", "").strip() == canonical:
                return dict(ch)

    return None


def match_channel_by_name_fuzzy(name: str) -> dict | None:
    """
    Fallback: try case-insensitive substring match.

    This is intentionally conservative — only returns a match when
    exactly one channel matches.
    """
    name_lower = name.strip().lower()
    candidates: list[dict] = []
    for ch in _channels:
        std = ch.get("standard_name", "").lower()
        if std and name_lower in std:
            candidates.append(ch)
    if len(candidates) == 1:
        return dict(candidates[0])
    return None