#!/usr/bin/env python3
"""只重处理缺失频道，缩小请求面，避免超时。"""
from __future__ import annotations

import json
import re
import threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from urllib.parse import quote
from urllib.request import Request, urlopen

REPO = "Hawaiine/Oasisic-IPTV"
JS_BASE = f"https://cdn.jsdelivr.net/gh/{REPO}@main/logo"
FAN_BASE = "https://live.fanmingming.com/tv"
FAN_IMG = "https://gcore.jsdelivr.net/gh/fanmingming/live@master/tv"
LOGO_DIR = Path("/opt/data/Oasisic-IPTV/logo")
CHANNELS = Path("/opt/data/Oasisic-IPTV/data/channels.json")
MISSING = Path("/opt/data/Oasisic-IPTV/data/logo_missing.txt")
GET_TIMEOUT = 8
MAX_BYTES = 120 * 1024
WORKERS = 10

_UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
_CN_RE = re.compile(r"[\u4e00-\u9fff]")


def _is_png(data: bytes) -> bool:
    return data.startswith(b"\x89PNG\r\n\x1a\n")


def _fetch(url: str) -> bytes | None:
    try:
        req = Request(url, headers=_UA)
        with urlopen(req, timeout=GET_TIMEOUT) as r:
            if r.status != 200:
                return None
            data = r.read(MAX_BYTES + 1)
            if len(data) > MAX_BYTES:
                return None
            if not _is_png(data):
                return None
            return data
    except Exception:
        return None


def _name_variants(ch: dict) -> list[str]:
    dis = (ch.get("display_name") or "").strip()
    std = (ch.get("standard_name") or "").strip()
    tid = (ch.get("tvg_id") or "").strip()
    seen: list[str] = []
    for v in (dis, std, tid):
        if v and v not in seen:
            seen.append(v)
    extras: list[str] = []
    tup = tid.upper()
    if tup == "CCTV5PLUS":
        extras += ["CCTV5+", "CCTV5plus", "CCTV-5+"]
    elif tup == "CCTV8K":
        extras += ["CCTV-8K", "CCTV4K"]
    elif tup == "CCTV4K":
        extras += ["CCTV-4K"]
    for base in (tid, dis):
        if base.endswith("卫视") and len(base) > 2:
            extras.append(base[:-2])
    if dis and dis.endswith("卫视") and len(dis) > 2:
        extras.append(dis[:-2] + "TV")
    extras += {
        "湖南卫视": ["Hunan", "HunanTV"],
        "东方卫视": ["Dragon", "DragonTV"],
        "东南卫视": ["SETV"],
        "海南卫视": ["Hainan", "HainanTV"],
        "河北卫视": ["Hebei", "HEBTV", "HebeiTV"],
        "山西卫视": ["Shanxi", "SXRTV", "ShanxiTV"],
        "大湾区卫视": ["GDWQ", "GreaterBay"],
        "南方卫视": ["GDNF", "SouthernTV"],
        "广东珠江": ["GDTVZJ", "Pearl River", "Zhujiang"],
        "广东体育": ["GDSports", "GuangdongSports"],
        "五星体育": ["ShanghaiSports", "FiveStarSports"],
        "北京体育": ["BeijingSports"],
    }.get(dis, [])
    for v in extras:
        if v and v not in seen:
            seen.append(v)
    return seen


def _candidate_urls(name: str) -> list[str]:
    enc = quote(name, safe="+")
    urls = [f"{FAN_BASE}/{enc}.png", f"{FAN_IMG}/{enc}.png"]
    if _CN_RE.search(name):
        urls.insert(0, f"{FAN_BASE}/{name}.png")
    return urls


def _download(ch: dict) -> str | None:
    tid = ch.get("tvg_id", "")
    if not tid:
        return None
    dest = LOGO_DIR / f"{tid}.png"
    if dest.exists() and dest.stat().st_size > 0:
        data = dest.read_bytes()
        if _is_png(data):
            return str(dest)
    for name in _name_variants(ch):
        for url in _candidate_urls(name):
            data = _fetch(url)
            if data:
                dest.write_bytes(data)
                return str(dest)
    return None


def sync() -> tuple[int, int]:
    LOGO_DIR.mkdir(parents=True, exist_ok=True)
    channels = json.loads(CHANNELS.read_text(encoding="utf-8"))
    missing_lock = threading.Lock()
    missing: list[str] = []
    updated = 0

    def _work(i: int) -> None:
        nonlocal updated
        ch = channels[i]
        tid = ch.get("tvg_id", "")
        if not tid:
            return
        # 只处理缺失频道；已有有效 PNG 跳过
        dest = LOGO_DIR / f"{tid}.png"
        if dest.exists() and dest.stat().st_size > 0:
            data = dest.read_bytes()
            if _is_png(data):
                ch["tvg_logo"] = f"{JS_BASE}/{tid}.png"
                return
        fname = _download(ch)
        if fname:
            ch["tvg_logo"] = f"{JS_BASE}/{tid}.png"
            notes = ch.get("notes")
            if isinstance(notes, str):
                ch["notes"] = notes.replace("logo_missing; ", "").replace("logo_missing", "").strip()
            updated += 1
        else:
            ch["tvg_logo"] = ""
            with missing_lock:
                missing.append(f"{tid}\t{ch.get('standard_name', '')}")

    with ThreadPoolExecutor(max_workers=WORKERS) as ex:
        list(ex.map(_work, range(len(channels))))

    CHANNELS.write_text(json.dumps(channels, ensure_ascii=False, indent=4) + "\n", encoding="utf-8")
    MISSING.write_text("\n".join(missing) + ("\n" if missing else ""), encoding="utf-8")
    n_files = sum(1 for p in LOGO_DIR.glob("*.png"))
    return n_files, len(missing)


if __name__ == "__main__":
    n_files, n_missing = sync()
    print(f"logo/ 文件数: {n_files}")
    print(f"仍缺失: {n_missing}")
    if MISSING.exists():
        txt = MISSING.read_text(encoding="utf-8").strip()
        if txt:
            print("缺失列表:")
            print(txt)
