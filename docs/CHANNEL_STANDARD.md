# 频道标准与收录规则

本文件是 `data/channels.json`（标准频道表）的规范说明。**主列表 `live.m3u` 只收标准表命中的频道**，
所以「往主列表加台」的正确做法是改表，而不是往主列表泄洪。

## 1. 收录判据（宁缺毋滥）

一个频道要进标准表，必须同时满足：

1. **确有直播源**：能在 `config/sources.yaml` 的公开源里采到（或至少有稳定公开源可加）；
2. **有上游 EPG**（推荐）：能在 `config/settings.yaml` 的 `epg_sources` 里找到带 programme 的 id；
   没有 EPG 的台也可以收，但会进 `data/epg_missing.txt`，且不享受「入表即有节目单」；
3. **名称符合规范**（见 §2），能归入 cctv / weishi / local / gangtai / sports / live 之一；
4. 不属于黑名单：点播回看、购物、测试、引流、博彩（见 `config/exclude.yaml`）。

> 判据 2 是当前扩容的主要来源：`scripts/suggest_channels.py` 会从 `live_more` 长尾里挑出
> 「归一化后能匹配到上游 EPG」的名字作为候选，避免收入一堆没有节目单的杂台。

## 2. 命名规范

| 类别 | 规范 | 例 | 反例 |
|------|------|----|------|
| 央视 | `CCTV-<数字> <节目名>`；付费/数字频道同形 | `CCTV-1 综合`、`CCTV-5+ 体育赛事`、`CCTV-4K 超高清`、`CCTV-世界地理` | `CCTV1`、`CCTV-01`、`CCTV1HD`、`世界地理` |
| 卫视 | 直接用台名，不加「高清/HD/卫视频道」 | `湖南卫视`、`东方卫视`、`东南卫视` | `上海东方卫视`、`HD 湖南卫视` |
| 各省市 | `<城市><频道名>`，城市在前 | `武汉新闻综合`、`广州影视`、`河南民生` | `武汉-1`、`WHTV1` |
| 港澳台 | 常用呼号 | `TVB翡翠台`、`凤凰卫视资讯台`、`澳视澳门` | `tvb jade`、`凤凰中文（香港）` |
| 体育 | 直接台名 | `五星体育`、`天元围棋`、`快乐垂钓` | `体育-1` |
| 网络直播 | 平台名/栏目名 | `湖南爱晚` | `直播间1` |

统一规则：**简体中文**（`zhconv` 清洗）；去掉分辨率、编码、运营商、IPv6、测试、备用、`HD/4K` 等后缀
（`4K` 频道作为独立台时保留在台名里，如 `CCTV-4K 超高清`）。

## 3. 字段规范

```jsonc
{
  "standard_name": "河南民生",              // 唯一主键，也是别名表的 key
  "display_name": "河南民生",               // 输出到 M3U 的显示名（默认同 standard_name）
  "category": "local",                      // cctv|weishi|local|gangtai|sports|live|overseas|hotel|radio|other
  "tvg_id": "河南民生",                      // 台标文件名（logo/<tvg_id>.png）；无台标时可为空
  "epg_id": "河南民生",                      // 输出到 #EXTINF 的 tvg-id；必须能命中上游且该 id 有 programme
  "tvg_logo": "https://cdn.jsdelivr.net/gh/Hawaiine/Oasisic-IPTV@main/logo/河南民生.png",
  "priority": 60,                           // 越小越优先（同频道多条 URL 竞争时使用）
  "notes": "long-tail"                      // 备注：long-tail 自动扩容 / curated 人工核定 / 空
}
```

硬规则：

- `epg_id` **禁止臆造**：只接受上游真实存在且**有 programme** 的 id；否则写 `null` 并进 `data/epg_missing.txt`；
- `tvg_logo` **只允许**本仓库 `logo/` 的 jsDelivr 地址（或留空）；禁止写第三方 URL（防 404）；
- 输出 M3U 时 `tvg-id = epg_id or tvg_id`（`settings.use_epg_id`），旧数据缺失 `epg_id` 也不会退化；
- `aliases.json` 的 key 必须是已存在的 `standard_name`（`zero-orphan` 校验）。

## 4. 怎么加台

```bash
# ① 从 live_more 长尾里找候选（只读，输出 data/channels_candidates.json）
python scripts/suggest_channels.py

# ② 复核候选后批量入库（幂等：已有的不会重复加）
python scripts/suggest_channels.py --apply

# ③ 补台标（上游镜像 → PNG 校验 → 落地 logo/ → 回填 tvg_logo）
python scripts/fetch_missing_logos.py

# ④ 对齐 EPG（新台自动补 epg_id 或进缺口清单）
python scripts/sync_epg_ids.py

# ⑤ 重新采集 + 校验
python scripts/collect.py && python scripts/fetch_epg.py && python scripts/verify_outputs.py
```

人工加台见 [ADD_CHANNEL.md](ADD_CHANNEL.md)。手动改表时至少给 `standard_name / display_name / category / tvg_id / epg_id`。

## 5. 分类兜底规则（未命中标准表时）

`scripts/lib/classify.py` 的关键词回退顺序：央视 → 港澳台 → 卫视 → 体育 → 直播 → 广播 → 酒店 →
（国内源）外文名/假名 → 国际；港澳台/东南亚华语台 → 港澳台；`直播` 结尾 → 网络直播；
省市名/台名前缀/频道类型词 → 各省市；兜底 → 其他。

目标：`live_more.m3u` 里「其他」占比持续下降（Phase 3 已从 73% → 50%），
剩余主要是点播轮播包（`NewTV` 系列等）、短代号与无类型词的杂名——**宁可留在「其他」也不乱分类**。

## 6. 黑名单（`config/exclude.yaml`）

命中即整条丢弃（不进主列表、不进扩展列表）：历年春晚回看、纯画质标签名、短大写代号、
数字开头的点播节目名、斗地主/棋牌、购物、测试/试看、加群/客服/代理、成人、博彩、预告/花絮、纯符号名。

黑名单是**配置**不是代码：想加规则直接改 YAML（支持正则），改完跑 `python -m pytest tests/test_exclude.py -q`
与 `python scripts/collect.py` 复核丢弃数量即可。