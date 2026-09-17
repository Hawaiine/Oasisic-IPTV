"""未命中标准表时的关键词分类回退。命中标准表的条目沿用表内 category。"""

from __future__ import annotations

import re
from typing import Any

from .categories import group_title, is_known

_RULES: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"CCTV|央视|CGTN|CETV|中国教育", re.I), "cctv"),
    # 凤凰卫视等必须先于「卫视」，否则会被误分为大陆卫视
    (re.compile(r"凤凰|TVB|翡翠|明珠|无线|HOY|ViuTV|Now\s*TV|中天|东森|华视|台视|中视|民视|TVBS|三立|澳门|澳视|RTHK|港台|纬来|爱尔达|ELEVEN", re.I), "gangtai"),
    (re.compile(r"卫视"), "weishi"),
    (re.compile(r"体育|赛事|足球|篮球|网球|乒乓|羽球|台球|高网|围棋|棋牌|电竞|NBA|英超|西甲|意甲|德甲|奥运|垂钓|钓鱼|赛车|武术", re.I), "sports"),
    (re.compile(r"斗鱼|虎牙|B站|哔哩|直播间|熊猫|快手"), "live"),
    (re.compile(r"电台|广播|调频|FM|AM\d|Radio|之声|CRI|CityFM", re.I), "radio"),
    (re.compile(r"酒店|Hotel", re.I), "hotel"),
]

# 地方台判据：① 省市名开头 ② 频道类型后缀（命中其一即视为「各省市」）
_REGIONS = (
    "北京|上海|天津|重庆|河北|山西|辽宁|吉林|黑龙江|江苏|浙江|安徽|福建|江西|山东|河南|湖北|湖南|广东|广西|海南|"
    "四川|贵州|云南|陕西|甘肃|青海|宁夏|新疆|西藏|内蒙古|延边|兵团|三沙|深圳|珠海|汕头|佛山|东莞|中山|惠州|"
    "广州|韶关|湛江|肇庆|江门|苏州|无锡|常州|南通|徐州|扬州|镇江|盐城|泰州|连云港|宿迁|淮安|杭州|宁波|温州|"
    "嘉兴|湖州|绍兴|金华|台州|丽水|衢州|舟山|济南|青岛|烟台|潍坊|临沂|济宁|淄博|泰安|聊城|德州|菏泽|枣庄|"
    "郑州|洛阳|开封|新乡|安阳|南阳|商丘|信阳|周口|驻马店|武汉|宜昌|襄阳|荆州|黄石|十堰|孝感|荆门|黄冈|咸宁|"
    "长沙|株洲|湘潭|衡阳|岳阳|常德|郴州|邵阳|益阳|永州|怀化|娄底|南昌|九江|赣州|上饶|宜春|吉安|抚州|景德镇|"
    "成都|绵阳|德阳|宜宾|南充|泸州|乐山|自贡|内江|遂宁|眉山|达州|广元|巴中|资阳|贵阳|遵义|六盘水|安顺|昆明|"
    "曲靖|玉溪|大理|红河|文山|西安|宝鸡|咸阳|渭南|榆林|汉中|延安|铜川|安康|商洛|兰州|天水|白银|西宁|银川|"
    "乌鲁木齐|拉萨|海口|三亚|南宁|柳州|桂林|梧州|北海|钦州|呼和浩特|包头|鄂尔多斯|赤峰|沈阳|大连|鞍山|抚顺|"
    "本溪|丹东|锦州|营口|长春|吉林市|哈尔滨|齐齐哈尔|大庆|牡丹江|佳木斯|石家庄|唐山|保定|邯郸|邢台|沧州|廊坊|"
    "秦皇岛|张家口|承德|衡水|太原|大同|临汾|运城|长治|晋城|福州|厦门|泉州|漳州|龙岩|三明|莆田|南平|宁德|合肥|"
    "芜湖|蚌埠|安庆|淮南|马鞍山|阜阳|宿州|六安|亳州|滁州|宣城|铜陵|池州|黄山"
)
_TYPES = (
    "新闻|综合|都市|影视|电影|影院|剧场|公共|少儿|卡通|动漫|动画|文艺|生活|经济|民生|综艺|科教|纪实|法治|文体|"
    "电视剧|影视剧|戏曲|农业|农村|资讯|频道|第一|影视娱乐|新闻综合|公共频道|经济生活|都市频道|影视娱乐频道|"
    "电信|移动|联通|有线|数字|音乐|旅游|美食|教育|演艺|求索|金色|纪实人文|纪实科教|国际频道"
)
_LOCAL_RE = re.compile(rf"^({_REGIONS})|({_TYPES})")


def classify_name(name: str, source_region: str = "") -> str:
    text = name or ""
    for pat, cat in _RULES:
        if pat.search(text):
            return cat
    if source_region == "hotel":
        return "hotel"
    if source_region == "overseas":
        return "overseas"
    if source_region in {"cn", "hk_tw"}:
        # ① 纯外文名 / 日文假名（聚合源里混入的海外台）→ 国际，避免堆在「其他」
        if re.search(r"[\u3040-\u30ff]", text):
            return "overseas"
        if not re.search(r"[\u4e00-\u9fff]", text) and re.search(r"[A-Za-z]{3,}", text):
            return "overseas"
        # ② 港澳台/东南亚华语台（放在「卫视」规则之后，避免误伤「香港卫视」）
        if re.search(r"台湾|香港|澳门|Astro|欢喜台|Astro", text):
            return "gangtai"
        # ③ 网络直播类命名
        if re.search(r"直播(室|间|台)?$", text):
            return "live"
        # ④ 地方台：电视台缩写前缀 / 省市名 / 频道类型词
        if re.match(r"^(BRTV|BTV|SMG|DRTV|JSBC|ZJTV|GDXW|HBS|CQTV|CDTV)", text, re.I):
            return "local"
        if _LOCAL_RE.search(text):
            return "local"
    return "other"


def classify_entries(entries: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for e in entries:
        rec = dict(e)
        cat = rec.get("category") or ""
        if rec.get("matched") and is_known(cat):
            rec["group_title"] = group_title(cat)
            out.append(rec)
            continue
        cat = classify_name(
            rec.get("cleaned_name") or rec.get("name") or "",
            rec.get("source_region") or "",
        )
        rec["category"] = cat
        rec["group_title"] = group_title(cat)
        out.append(rec)
    return out
