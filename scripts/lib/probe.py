# coding: utf-8
"""
Stream availability probe (stub — full implementation in Phase 5).

Current stub provides the public API signatures so caller code can be
written against stable interfaces.

Functions
---------
check_stream(url, timeout=10) -> bool
    Return True if the stream URL is reachable (stub: always True).
probe_channels(channels, concurrency=5, timeout=10) -> list[dict]
    Run check_stream on a list of channel dicts and annotate with
    ``alive`` key (stub: all alive).
"""

from __future__ import annotations

import asyncio
import typing as t


async def check_stream(url: str, timeout: int = 10) -> bool:
    """
    Check whether a stream URL is reachable.

    Parameters
    ----------
    url : str
        Stream URL (typically an m3u8 playlist).
    timeout : int
        Per-request timeout in seconds.

    Returns
    -------
    bool
        True if the stream responds successfully.
    """
    # ── Stub ───────────────────────────────────────────────────────
    # Phase 5: HTTP HEAD + m3u8 sub-segment verification
    _ = url, timeout
    return True


async def probe_channels(
    channels: list[dict[str, t.Any]],
    concurrency: int = 5,
    timeout: int = 10,
) -> list[dict[str, t.Any]]:
    """
    Run availability checks on a list of channel dicts.

    Each channel dict is annotated with an ``alive`` key.

    Parameters
    ----------
    channels : list[dict]
        Channel dicts with at least a ``url`` key.
    concurrency : int
        Maximum concurrent probes.
    timeout : int
        Per-request timeout in seconds.

    Returns
    -------
    list[dict]
        Channel dicts with ``alive`` boolean added.
    """
    # ── Stub ───────────────────────────────────────────────────────
    # Phase 5: semaphore-bound async pool
    _ = concurrency, timeout
    for ch in channels:
        ch["alive"] = True
    return channels