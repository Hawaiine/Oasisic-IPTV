# coding: utf-8
"""
M3U parsing and generation utilities.

Functions
---------
parse_m3u_content(text, source_name) -> list[dict]
    Parse M3U playlist text into a list of channel dicts.
generate_m3u(channels, path, title)
    Write a list of channel dicts to an M3U file.
count_extinf(path) -> int
    Count the number of ``#EXTINF`` entries in an M3U file.
"""

from __future__ import annotations

import os
import re
import typing as t

# ── Regex ──────────────────────────────────────────────────────────

_EXTINF_RE = re.compile(
    r'#EXTINF\s*:\s*-?\d+\s*(?:[^,]*,)(.+)',
    re.IGNORECASE,
)

# ── Public API ─────────────────────────────────────────────────────


def parse_m3u_content(text: str, source_name: str) -> list[dict[str, t.Any]]:
    """
    Parse M3U playlist text.

    Parameters
    ----------
    text : str
        Raw M3U content.
    source_name : str
        Identifier for the source (used for debugging / provenance).

    Returns
    -------
    list[dict]
        Each dict has keys: ``name``, ``url``, ``tvg_id``, ``tvg_name``,
        ``tvg_logo``, ``group_title``, ``source``.
    """
    channels: list[dict[str, t.Any]] = []
    lines = text.splitlines()
    current: dict[str, t.Any] | None = None

    for line in lines:
        stripped = line.strip()

        # Skip empty lines and EXTM3U header
        if not stripped or stripped.upper().startswith("#EXTM3U"):
            continue

        # Parse EXTINF
        m = _EXTINF_RE.match(stripped)
        if m:
            current = {
                "name": (m.group(1) or "").strip(),
                "url": "",
                "tvg_id": "",
                "tvg_name": "",
                "tvg_logo": "",
                "group_title": "",
                "source": source_name,
            }

            # Parse attribute-like tags embedded in the EXTINF line
            # e.g. tvg-id="CCTV1" tvg-name="CCTV-1" tvg-logo="..."
            for attr in ("tvg-id", "tvg-name", "tvg-logo"):
                am = re.search(
                    rf'{re.escape(attr)}\s*=\s*"([^"]*)"', stripped, re.IGNORECASE
                )
                if am:
                    current[attr.replace("-", "_")] = am.group(1)

            # group-title
            gm = re.search(
                r'group-title\s*=\s*"([^"]*)"', stripped, re.IGNORECASE
            )
            if gm:
                current["group_title"] = gm.group(1)

            continue

        # EXTGRP (legacy group title)
        if stripped.upper().startswith("#EXTGRP:"):
            if current is not None:
                current["group_title"] = stripped.split(":", 1)[1].strip()
            continue

        # EXTVLCOPT / KODIPROP — skip
        if stripped.upper().startswith(("#EXTVLCOPT:", "#KODIPROP:")):
            continue

        # URL line
        if current is not None and not stripped.startswith("#"):
            current["url"] = stripped
            channels.append(current)
            current = None

    return channels


def generate_m3u(
    channels: list[dict[str, t.Any]],
    path: str,
    title: str = "Oasisic-IPTV",
) -> None:
    """
    Write a list of channel dicts to an M3U file.

    Parameters
    ----------
    channels : list[dict]
        Channel dicts with keys ``name``, ``url``, ``tvg_id``, ``tvg_logo``,
        ``group_title``.
    path : str
        Output file path.
    title : str
        Playlist title (written in the #EXTM3U header).
    """
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)

    with open(path, "w", encoding="utf-8") as f:
        f.write(f"#EXTM3U\n")
        for ch in channels:
            # Build EXTINF line
            attrs = ""
            if ch.get("tvg_id"):
                attrs += f' tvg-id="{ch["tvg_id"]}"'
            if ch.get("tvg_logo"):
                attrs += f' tvg-logo="{ch["tvg_logo"]}"'
            if ch.get("group_title"):
                attrs += f' group-title="{ch["group_title"]}"'

            name = ch.get("name", "Unknown")
            f.write(f"#EXTINF:-1{attrs},{name}\n")
            f.write(f"{ch['url']}\n")


def count_extinf(path: str) -> int:
    """
    Count the number of ``#EXTINF`` entries in an M3U file.

    Parameters
    ----------
    path : str
        Path to the M3U file.

    Returns
    -------
    int
    """
    if not os.path.isfile(path):
        return 0
    count = 0
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        for line in f:
            if line.strip().upper().startswith("#EXTINF"):
                count += 1
    return count