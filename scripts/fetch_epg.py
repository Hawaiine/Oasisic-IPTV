# coding: utf-8
"""
Oasisic-IPTV EPG 合并脚本。

从多个 EPG 源下载 XML，合并后输出 output/guide.xml。

环境变量
--------
EPG_TIMEOUT : int
    单源下载超时秒数（默认 30）。
MAX_SOURCE_BYTES : int
    单源最大字节数（默认 10_000_000 = 10MB）。

失败策略
--------
EPG 失败不会导致 collect 整 job 失败 — 仅打印警告。
"""

from __future__ import annotations

import os
import sys
import typing as t
import xml.etree.ElementTree as ET
from urllib import request

_SCRIPTS_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__)))
if _SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, _SCRIPTS_DIR)

from lib.io_util import load_yaml, project_root, save_json

# ── EPG sources ────────────────────────────────────────────────────

_DEFAULT_SOURCES: list[dict[str, t.Any]] = [
    {"name": "epgshare01", "url": "https://epgshare01.online/epgshare01/epg_ripper_CN1.xml"},
    {"name": "epgshare02", "url": "https://epgshare01.online/epgshare01/epg_ripper_CN2.xml"},
    {"name": "iptvx", "url": "https://epg.iptvx.one/e.xml"},
    {"name": "fanmingming", "url": "https://live.fanmingming.cn/e.xml"},
]

_MAX_BYTES = int(os.environ.get("MAX_SOURCE_BYTES", "10_000_000"))
_TIMEOUT = int(os.environ.get("EPG_TIMEOUT", "30"))
_USER_AGENT = "Mozilla/5.0 (compatible; Oasisic-IPTV/1.0)"


def _fetch_xml(url: str, name: str) -> str | None:
    """Fetch an XML file from URL. Returns content or None on failure."""
    headers = {"User-Agent": _USER_AGENT}
    req = request.Request(url, headers=headers)
    try:
        with request.urlopen(req, timeout=_TIMEOUT) as resp:
            if resp.status != 200:
                print(f"   ⚠️ {name}: HTTP {resp.status}")
                return None
            content = resp.read(_MAX_BYTES)
            text = content.decode("utf-8", errors="replace")
            if not text.strip().startswith("<?xml") and not text.strip().startswith("<tv"):
                print(f"   ⚠️ {name}: 非 XML 内容")
                return None
            print(f"   ✅ {name}: {len(text)} bytes")
            return text
    except Exception as exc:
        print(f"   ⚠️ {name}: {exc}")
        return None


def _merge_epg(xml_texts: list[str]) -> str:
    """Merge multiple EPG XML documents into one."""
    root = ET.Element("tv", attrib={"generator-info-name": "Oasisic-IPTV"})

    seen_channels: set[str] = set()
    seen_programmes: set[tuple[str, str, str]] = set()

    for xml_text in xml_texts:
        try:
            tree = ET.fromstring(xml_text)
        except ET.ParseError as e:
            print(f"   ⚠️ XML 解析错误: {e}")
            continue

        # Merge <channel> elements
        for ch in tree.findall("channel"):
            ch_id = ch.get("id", "")
            if ch_id and ch_id not in seen_channels:
                seen_channels.add(ch_id)
                root.append(ch)

        # Merge <programme> elements (deduplicate by channel+start+title)
        for prog in tree.findall("programme"):
            start = prog.get("start", "")
            ch_id = prog.get("channel", "")
            title_el = prog.find("title")
            title = title_el.text if title_el is not None else ""
            key = (ch_id, start, title or "")
            if key not in seen_programmes:
                seen_programmes.add(key)
                root.append(prog)

    return ET.tostring(root, encoding="unicode", xml_declaration=True)


def main() -> None:
    # Load EPG sources from settings (with fallback)
    settings_path = os.path.join(project_root(), "config", "settings.yaml")
    epg_sources = _DEFAULT_SOURCES
    try:
        settings = load_yaml(settings_path)
        if settings and "epg_sources" in settings:
            epg_sources = settings["epg_sources"]
    except Exception:
        pass

    print("📡 下载 EPG ...")
    xml_texts: list[str] = []
    for src in epg_sources:
        content = _fetch_xml(src["url"], src["name"])
        if content:
            xml_texts.append(content)

    if not xml_texts:
        print("⚠️  无可用 EPG 源，跳过")
        return

    print(f"🔄 合并 {len(xml_texts)} 个 EPG 源 ...")
    merged = _merge_epg(xml_texts)

    output_dir = os.path.join(project_root(), "output")
    os.makedirs(output_dir, exist_ok=True)
    guide_path = os.path.join(output_dir, "guide.xml")
    with open(guide_path, "w", encoding="utf-8") as f:
        f.write(merged)
    print(f"✅ guide.xml: {len(merged)} bytes")


if __name__ == "__main__":
    main()