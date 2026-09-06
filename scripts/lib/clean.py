"""频道名清洗：简体、去标签、央视/卫视强制规范。"""

from __future__ import annotations

import re
import unicodedata

try:
    import zhconv
except ImportError:  # pragma: no cover
    zhconv = None  # type: ignore[assignment]

# CCTV 数字台 → 节目名。4K/8K/5+ 单独处理。
_CCTV_PROGRAM: dict[str, str] = {
    "1": "综合",
    "2": "财经",
    "3": "综艺",
    "4": "中文国际",
    "5": "体育",
    "6": "电影",
    "7": "国防军事",
    "8": "电视剧",
    "9": "纪录",
    "10": "科教",
    "11": "戏曲",
    "12": "社会与法",
    "13": "新闻",
    "14": "少儿",
    "15": "音乐",
    "16": "奥林匹克",
    "17": "农业农村",
}

# 卫视别名统一
_WEISHI_FIX: dict[str, str] = {
    "上海东方卫视": "东方卫视",
    "东方卫视频道": "东方卫视",
    "上海卫视": "东方卫视",
    "dragon tv": "东方卫视",
    "福建东南卫视": "东南卫视",
    "东南卫视频道": "东南卫视",
    "旅游卫视": "海南卫视",
    "兵团卫视频道": "兵团卫视",
}

# 分辨率 / 编码 / 运营商 / 状态标签（CCTV-4K/8K 频道名除外）
_TAG_RE = re.compile(
    r"""
    (?:
        \b(?:FHD|UHD|HD|SD|HDR|HEVC|H\.?265|H\.?264|AVC|AAC)\b
      | (?:超高清|高清|超清|蓝光|标清|流畅)
      | (?:50\s*FPS|60\s*FPS)
      | (?:IPV?6|IPv6|ipv6)
      | (?:测试|备用|备份|临时|实验)
      | (?:移动|联通|电信|广电)
      | (?:频道)
    )
    """,
    re.IGNORECASE | re.VERBOSE,
)

_BRACKETS_RE = re.compile(r"[\[【（(][^\]】）)]*[\]】）)]")
_EMOJI_RE = re.compile(
    "["
    "\U0001f300-\U0001faff"
    "\U00002700-\U000027bf"
    "\U0001f600-\U0001f64f"
    "]+",
    flags=re.UNICODE,
)
_MULTI_SPACE = re.compile(r"\s+")

# CCTV5+ / CCTV-5+ / 五加
_CCTV5P_RE = re.compile(
    r"\bCCTV\s*[-_]?\s*5\s*\+|CCTV5Plus|CCTV5\+|央视(?:五|5)\s*加",
    re.IGNORECASE,
)
_CCTV4K_RE = re.compile(r"\bCCTV\s*[-_]?\s*4K\b|央视4K", re.IGNORECASE)
_CCTV8K_RE = re.compile(r"\bCCTV\s*[-_]?\s*8K\b|央视8K", re.IGNORECASE)

# 捕获数字 + 可选分隔符，避免贪婪 \s* 在「CCTV1综合」中间插空格
# 数字后不能用 \b：Python \w 含汉字，「CCTV1综合」里 1 和 综之间没有词界
_CCTV_NUM_RE = re.compile(
    r"\bCCTV\s*[-_]?\s*0*(\d{1,2})(?!\d)",
    re.IGNORECASE,
)
_CCTV_CN_RE = re.compile(r"央视\s*(\d{1,2})\s*套?")


def to_simplified(name: str) -> str:
    if zhconv is None:
        return name
    return zhconv.convert(name, "zh-cn")


def _strip_tags(name: str) -> str:
    # 先保护 4K/8K 真台名
    sentinel_4k = "\u0000CCTV4K\u0000"
    sentinel_8k = "\u0000CCTV8K\u0000"
    name = _CCTV4K_RE.sub(sentinel_4k, name)
    name = _CCTV8K_RE.sub(sentinel_8k, name)
    name = _BRACKETS_RE.sub(" ", name)
    name = _TAG_RE.sub(" ", name)
    name = name.replace(sentinel_4k, "CCTV-4K")
    name = name.replace(sentinel_8k, "CCTV-8K")
    return name


def _normalize_cctv(name: str) -> str:
    if _CCTV5P_RE.search(name):
        return "CCTV-5+ 体育赛事"
    if "CCTV-4K" in name or _CCTV4K_RE.search(name):
        return "CCTV-4K 超高清"
    if "CCTV-8K" in name or _CCTV8K_RE.search(name):
        return "CCTV-8K 超高清"

    m = _CCTV_NUM_RE.search(name) or _CCTV_CN_RE.search(name)
    if not m:
        return name
    num = str(int(m.group(1)))
    prog = _CCTV_PROGRAM.get(num)
    if not prog:
        return f"CCTV-{num}"
    return f"CCTV-{num} {prog}"


def _normalize_weishi(name: str) -> str:
    key = name.strip().lower()
    for raw, canon in _WEISHI_FIX.items():
        if raw.lower() in key or name.strip() == raw:
            return canon
    # 「XX卫视频道」→「XX卫视」
    name = re.sub(r"卫视频道$", "卫视", name)
    name = re.sub(r"卫视高清$", "卫视", name)
    return name


def clean_channel_name(raw: str) -> str:
    """对外清洗入口。返回可用于匹配的干净名称（简体、无标签）。"""
    if not raw:
        return ""
    name = unicodedata.normalize("NFC", raw)
    name = to_simplified(name)
    name = _EMOJI_RE.sub("", name)
    name = name.replace("|", " ").replace("_", " ").replace("-", "-")
    name = _strip_tags(name)
    name = _MULTI_SPACE.sub(" ", name).strip(" -_/|")
    name = _normalize_cctv(name)
    name = _normalize_weishi(name)
    name = _MULTI_SPACE.sub(" ", name).strip()
    return name
