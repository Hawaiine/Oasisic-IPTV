# coding: utf-8
"""
Stream availability probe for Oasisic-IPTV.

Verifies m3u8 streams by:
1. Fetching the m3u8 playlist (HTTP HEAD + GET)
2. Parsing the first segment URL from the playlist
3. Verifying the first segment is accessible

Concurrency controlled via PROBE_CONCURRENCY (default 10) and
PROBE_TIMEOUT (default 10) env vars or settings.

Functions
---------
check_stream(url, timeout=10, headers=None) -> dict
    Return dict with alive, latency_ms, status, error fields.
probe_channels(channels, concurrency=10, timeout=10, headers=None) -> list[dict]
    Annotate channel dicts with alive, latency_ms, status.
"""

from __future__ import annotations

import asyncio
import os
import time
import typing as t

import aiohttp

# ── Defaults ───────────────────────────────────────────────────────

_DEFAULT_CONCURRENCY = int(os.environ.get("PROBE_CONCURRENCY", "10"))
_DEFAULT_TIMEOUT = int(os.environ.get("PROBE_TIMEOUT", "10"))
_USER_AGENT = "Mozilla/5.0 (compatible; Oasisic-IPTV/1.0)"


async def _check_one(
    url: str,
    timeout: int,
    session: aiohttp.ClientSession,
    sem: asyncio.Semaphore,
) -> dict[str, t.Any]:
    """Check a single stream URL. Returns dict with probe results."""
    async with sem:
        start = time.monotonic()
        result: dict[str, t.Any] = {
            "url": url,
            "alive": False,
            "latency_ms": 0,
            "status": "",
            "error": "",
        }
        try:
            # Step 1: HEAD the m3u8 playlist
            async with session.head(
                url,
                timeout=aiohttp.ClientTimeout(total=timeout),
                allow_redirects=True,
            ) as resp:
                if resp.status != 200:
                    latency = int((time.monotonic() - start) * 1000)
                    result["latency_ms"] = latency
                    result["status"] = f"HTTP {resp.status}"
                    return result

            # Step 2: GET the playlist content
            async with session.get(
                url,
                timeout=aiohttp.ClientTimeout(total=timeout),
                allow_redirects=True,
            ) as resp:
                if resp.status != 200:
                    latency = int((time.monotonic() - start) * 1000)
                    result["latency_ms"] = latency
                    result["status"] = f"HTTP {resp.status}"
                    return result

                content = await resp.read()

            # Step 3: Parse m3u8 to find first segment
            text = content.decode("utf-8", errors="replace")
            seg_url = None
            for line in text.splitlines():
                line = line.strip()
                if line and not line.startswith("#"):
                    # Relative or absolute URL
                    if line.startswith("http://") or line.startswith("https://"):
                        seg_url = line
                    else:
                        # Relative to the playlist URL
                        base = url.rsplit("/", 1)[0]
                        seg_url = f"{base}/{line.lstrip('/')}"
                    break

            if seg_url is None:
                latency = int((time.monotonic() - start) * 1000)
                result["latency_ms"] = latency
                result["status"] = "no_segment"
                return result

            # Step 4: Verify first segment
            async with session.head(
                seg_url,
                timeout=aiohttp.ClientTimeout(total=timeout),
                allow_redirects=True,
            ) as resp:
                latency = int((time.monotonic() - start) * 1000)
                result["latency_ms"] = latency
                if resp.status == 200:
                    result["alive"] = True
                    result["status"] = "ok"
                else:
                    result["status"] = f"seg_HTTP {resp.status}"

        except asyncio.TimeoutError:
            latency = int((time.monotonic() - start) * 1000)
            result["latency_ms"] = latency
            result["status"] = "timeout"
            result["error"] = "timeout"
        except aiohttp.ClientError as exc:
            latency = int((time.monotonic() - start) * 1000)
            result["latency_ms"] = latency
            result["status"] = "error"
            result["error"] = str(exc)[:120]
        except Exception as exc:
            latency = int((time.monotonic() - start) * 1000)
            result["latency_ms"] = latency
            result["status"] = "error"
            result["error"] = str(exc)[:120]

        return result


async def check_stream(
    url: str,
    timeout: int = 10,
    headers: dict[str, str] | None = None,
) -> dict[str, t.Any]:
    """
    Check whether a stream URL is reachable.

    Returns
    -------
    dict with keys: alive, latency_ms, status, error, url.
    """
    hdrs = dict(headers or {})
    hdrs.setdefault("User-Agent", _USER_AGENT)
    connector = aiohttp.TCPConnector(limit_per_host=2)
    sem = asyncio.Semaphore(1)
    async with aiohttp.ClientSession(headers=hdrs, connector=connector) as session:
        return await _check_one(url, timeout, session, sem)


async def probe_channels(
    channels: list[dict[str, t.Any]],
    concurrency: int = 10,
    timeout: int = 10,
    headers: dict[str, str] | None = None,
) -> list[dict[str, t.Any]]:
    """
    Run availability checks on a list of channel dicts.

    Each channel dict is annotated with:
      - alive (bool)
      - latency_ms (int)
      - probe_status (str)

    Channels are returned in the same order (with probe results added).
    A ``probe_map`` URL→result dict is also available for reference.

    Parameters
    ----------
    channels : list[dict]
        Channel dicts with at least a ``url`` key.
    concurrency : int
        Maximum concurrent probes.
    timeout : int
        Per-request timeout in seconds.
    headers : dict | None
        Extra HTTP headers.

    Returns
    -------
    list[dict]
        Channel dicts with probe annotations.
    """
    hdrs = dict(headers or {})
    hdrs.setdefault("User-Agent", _USER_AGENT)
    connector = aiohttp.TCPConnector(limit_per_host=5)
    sem = asyncio.Semaphore(concurrency)
    seen_urls: dict[str, dict[str, t.Any]] = {}
    total = len(channels)

    async with aiohttp.ClientSession(headers=hdrs, connector=connector) as session:
        # Deduplicate URLs
        url_to_indices: dict[str, list[int]] = {}
        for i, ch in enumerate(channels):
            url = ch.get("url", "")
            if url:
                url_to_indices.setdefault(url, []).append(i)

        tasks = []
        for url in url_to_indices:
            tasks.append(_check_one(url, timeout, session, sem))

        results = await asyncio.gather(*tasks)

        # Map results back to channels
        for url, result in zip(url_to_indices, results):
            seen_urls[url] = result
            for idx in url_to_indices[url]:
                channels[idx]["alive"] = result["alive"]
                channels[idx]["latency_ms"] = result["latency_ms"]
                channels[idx]["probe_status"] = result["status"]

    # Print summary
    ok_count = sum(1 for r in seen_urls.values() if r["alive"])
    print(f"   📡 测活: {ok_count}/{len(seen_urls)} 可用, "
          f"{total} 条频道")

    return channels