#!/usr/bin/env python3
"""Sync standard-channel logos into logo/ and rewrite channels.json tvg_logo."""
from __future__ import annotations

import json
import re
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from urllib.request import Request, urlopen

REPO = "Hawaiine/Oasisic-IPTV"
JS_BASE = f"https://cdn.jsdelivr.net/gh/{REPO}@main/logo"
FAN_BASE = "https://live.fanmingming.com/tv"
CCSH_BASE = "https://raw.githubusercontent.com/CCSH/IPTV/main/logo"
LOGO_DIR = Path("/opt/data/Oasisic-IPTV/logo")
CHANNELS = Path("/opt/data/Oasisic-IPTV/data/channels.json")
MISSING = Path("/opt/data/Oasisic-IPTV/data/logo_missing.txt")
HEAD_TIMEOUT = 8
GET_TIMEOUT = 12
MAX_BYTES = 100 * 1024
WORKERS = 12

_VARIANTS: dict[str, list[str]] = {
    "CCTV5Plus": ["CCTV5Plus", "CCTV5+", "CCTV-5+"],
    "CCTV8K": ["CCTV8K", "CCTV-8K", "CCTV4K"],
    "CCTV4K": ["CCTV4K", "CCTV-4K"],
    "CCTV5+": ["CCTV5+", "CCTV5Plus", "CCTV-5+"],
    "CCTV1": ["CCTV1", "CCTV-1"],
    "CCTV2": ["CCTV2", "CCTV-2"],
    "CCTV3": ["CCTV3", "CCTV-3"],
    "CCTV4": ["CCTV4", "CCTV-4"],
    "CCTV6": ["CCTV6", "CCTV-6"],
    "CCTV7": ["CCTV7", "CCTV-7"],
    "CCTV8": ["CCTV8", "CCTV-8"],
    "CCTV9": ["CCTV9", "CCTV-9"],
    "CCTV10": ["CCTV10", "CCTV-10"],
    "CCTV11": ["CCTV11", "CCTV-11"],
    "CCTV12": ["CCTV12", "CCTV-12"],
    "CCTV13": ["CCTV13", "CCTV-13"],
    "CCTV14": ["CCTV14", "CCTV-14"],
    "CCTV15": ["CCTV15", "CCTV-15"],
    "CCTV16": ["CCTV16", "CCTV-16"],
    "CCTV17": ["CCTV17", "CCTV-17"],
    "CGTNDoc": ["CGTNDoc", "CGTN-Doc", "CGTN-Documentary"],
    "BeijingSports": ["BeijingSports"],
    "WHTV": ["WHTV", "WuhanNews", "WuhanNewsIntegrated", "WHTV"],
    "CDXW": ["CDXW", "CDTV-1", "ChengduNewsIntegrated", "ChengduNews"],
    "WHWY": ["WHWY", "WuhanArt", "WuhanWenyi", "WuhanLiterature", "WuhanCulture"],
    "BTVWY": ["BTVWY", "BeijingNews"],
    "BTVXW": ["BTVXW", "BeijingXinwen", "BeijingNews"],
    "BTVYS": ["BTVYS", "BeijingYiShu", "BeijingArts"],
    "BTTV": ["BTTV", "BeijingTraffic"],
    "AHJJ": ["AHJJ", "AnhuiJJ", "AnhuiEconomics"],
}


def _name_variants(ch: dict) -> list[str]:
    tid = ch.get("tvg_id", "")
    variants = _VARIANTS.get(tid.upper(), [tid])
    seen: list[str] = []
    for v in [tid] + variants:
        if v not in seen:
            seen.append(v)
    return seen


def _is_png(data: bytes) -> bool:
    return data.startswith(b"\x89PNG\r\n\x1a\n")


def _head_exists(url: str) -> bool:
    try:
        req = Request(url, method="HEAD", headers={"User-Agent": "Mozilla/5.0"})
        with urlopen(req, timeout=HEAD_TIMEOUT) as r:
            return r.status == 200 and "image/png" in r.headers.get("Content-Type", "")
    except Exception:
        return False


def _fetch(url: str) -> bytes | None:
    try:
        req = Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urlopen(req, timeout=GET_TIMEOUT) as r:
            data = r.read(MAX_BYTES + 1)
            if len(data) > MAX_BYTES:
                return None
            if r.status == 200 and _is_png(data):
                return data
    except Exception:
        return None
    return None


def _try_names(names: list[str]) -> tuple[str, bytes] | None:
    checked = set()
    urls: list[tuple[str, str]] = []
    for name in names:
        key = f"{FAN_BASE}/{name}.png"
        if key not in checked:
            checked.add(key)
            urls.append((name, key))
        stripped = re.sub(r"^(logo|tv|tvlogo)-?", "", name, flags=re.IGNORECASE)
        if stripped != name:
            key = f"{CCSH_BASE}/{stripped}.png"
            if key not in checked:
                checked.add(key)
                urls.append((name, key))
        key = f"{CCSH_BASE}/{name}.png"
        if key not in checked:
            checked.add(key)
            urls.append((name, key))
    # first pass HEAD
    for name, url in urls:
        if _head_exists(url):
            data = _fetch(url)
            if data:
                return name, data
    return None


def sync() -> tuple[int, int]:
    LOGO_DIR.mkdir(parents=True, exist_ok=True)
    channels = json.loads(CHANNELS.read_text(encoding="utf-8"))
    missing_paths = []
    updated = 0
    skipped = 0

    def _process(ch: dict) -> None:
        nonlocal updated, skipped
        tid = ch.get("tvg_id", "")
        if not tid:
            skipped += 1
            return
        dest = LOGO_DIR / f"{tid}.png"
        if dest.exists() and dest.stat().st_size > 0:
            data = dest.read_bytes()
            if not _is_png(data):
                dest.unlink(missing_ok=True)
            else:
                ch["tvg_logo"] = f"{JS_BASE}/{tid}.png"
                notes = ch.get("notes") or ""
                if isinstance(notes, str):
                    ch["notes"] = notes.replace("logo_missing; ", "").replace("logo_missing", "").strip()
                updated += 1
                return
        result = _try_names(_name_variants(ch))
        if result:
            name, data = result
            dest.write_bytes(data)
            ch["tvg_logo"] = f"{JS_BASE}/{tid}.png"
            notes = ch.get("notes") or ""
            if isinstance(notes, str):
                ch["notes"] = notes.replace("logo_missing; ", "").replace("logo_missing", "").strip()
            updated += 1
        else:
            ch["tvg_logo"] = ""
            missing_paths.append(f"{tid}\t{ch.get('standard_name', '')}")
            updated += 1

    with ThreadPoolExecutor(max_workers=WORKERS) as executor:
        list(executor.map(_process, channels))

    CHANNELS.write_text(json.dumps(channels, ensure_ascii=False, indent=4) + "\n", encoding="utf-8")
    MISSING.write_text("\n".join(missing_paths) + ("\n" if missing_paths else ""), encoding="utf-8")
    return updated, len(missing_paths)


def verify_remote() -> tuple[int, int]:
    channels = json.loads(CHANNELS.read_text(encoding="utf-8"))
    ok = 0
    fail = 0
    for ch in channels:
        url = ch.get("tvg_logo", "")
        if not url:
            continue
        try:
            req = Request(url, method="HEAD", headers={"User-Agent": "Mozilla/5.0"})
            with urlopen(req, timeout=HEAD_TIMEOUT) as r:
                if r.status == 200:
                    ok += 1
                else:
                    fail += 1
        except Exception:
            fail += 1
    return ok, fail


if __name__ == "__main__":
    updated, missing = sync()
    print(f"synced logos: {updated} updated, {missing} missing")
    if MISSING.exists():
        txt = MISSING.read_text(encoding="utf-8").strip()
        if txt:
            print("missing ids:")
            print(txt)
    ok, fail = verify_remote()
    print(f"remote verify: {ok} OK, {fail} fail")
