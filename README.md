# Oasisic-IPTV

[![collect](https://github.com/Hawaiine/Oasisic-IPTV/actions/workflows/collect.yml/badge.svg)](https://github.com/Hawaiine/Oasisic-IPTV/actions/workflows/collect.yml)
[![License](https://img.shields.io/github/license/Hawaiine/Oasisic-IPTV)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.11+-blue)](https://www.python.org/)

公开 IPTV 源日更聚合工具 —— 多源采集、智能清洗、标准命名、目录制选优，生成干净可用的分类 M3U 播放列表。

Oasisic-IPTV 面向中文用户。它每日从多个公开源采集频道，经过名称清洗、标准频道表匹配、中文分类和一台一链选优后，输出结构清晰的 M3U，可导入 VLC、PotPlayer、TVBox、TiviMate、Kodi。

项目坚持目录制：主列表 `live.m3u` 只保留命中标准表的频道，且每台一条最优链接；`live_backup.m3u` 为同一批标准台保留最多 3 条不同 URL（给会自动切换的播放器）；扩展列表 `live_more.m3u` 保留未入表频道。源的新增、禁用、连续失败自动下线都走配置，不必改代码。

**不进行任何流媒体测活。** 收录不代表实时可播，请遵守当地法律法规。

---

## 订阅链接

| 文件 | 说明 |
|------|------|
| [`live.m3u`](https://raw.githubusercontent.com/Hawaiine/Oasisic-IPTV/main/output/live.m3u) | 精选目录，一台一链 |
| [`live_backup.m3u`](https://raw.githubusercontent.com/Hawaiine/Oasisic-IPTV/main/output/live_backup.m3u) | 标准台备份，每台最多 3 条 URL |
| [`live_more.m3u`](https://raw.githubusercontent.com/Hawaiine/Oasisic-IPTV/main/output/live_more.m3u) | 扩展列表（未入标准表） |
| [`live_cctv.m3u`](https://raw.githubusercontent.com/Hawaiine/Oasisic-IPTV/main/output/live_cctv.m3u) | 央视 |
| [`live_weishi.m3u`](https://raw.githubusercontent.com/Hawaiine/Oasisic-IPTV/main/output/live_weishi.m3u) | 卫视 |
| [`live_local.m3u`](https://raw.githubusercontent.com/Hawaiine/Oasisic-IPTV/main/output/live_local.m3u) | 各省市 |
| [`live_gangtai.m3u`](https://raw.githubusercontent.com/Hawaiine/Oasisic-IPTV/main/output/live_gangtai.m3u) | 港澳台 |
| [`live_sports.m3u`](https://raw.githubusercontent.com/Hawaiine/Oasisic-IPTV/main/output/live_sports.m3u) | 体育 |
| [`live_live.m3u`](https://raw.githubusercontent.com/Hawaiine/Oasisic-IPTV/main/output/live_live.m3u) | 网络直播 |
| [`live_overseas.m3u`](https://raw.githubusercontent.com/Hawaiine/Oasisic-IPTV/main/output/live_overseas.m3u) | 国际（默认不进主列表） |
| [`live_special.m3u`](https://raw.githubusercontent.com/Hawaiine/Oasisic-IPTV/main/output/live_special.m3u) | 酒店 |
| [`live_radio.m3u`](https://raw.githubusercontent.com/Hawaiine/Oasisic-IPTV/main/output/live_radio.m3u) | 电台（独立文件） |
| [`guide.xml`](https://raw.githubusercontent.com/Hawaiine/Oasisic-IPTV/main/output/guide.xml) | 裁剪版 EPG（仅标准表频道） |

主列表 `#EXTM3U` 已写入 `url-tvg="https://live.fanmingming.com/e.xml"`，支持自动读取的播放器可直接出节目单。手动填写时用同一地址。裁剪版 `guide.xml` 体积更小，稳定后会把 `url-tvg` 切到自建地址。

---

## 可播口径

- **收录 ≠ 可播。** 列表只保证「公开源里出现过、经过清洗和选优」，不探测 HLS/TS 是否当前可播。
- 地域源、IPv6、酒店源、`rtp://` 组播可以收录；`rtp://` 会降权排后。
- 国际频道默认只出现在 `live_overseas.m3u` / `live_more.m3u`。
- 主列表一台一链：同一频道名最多 1 条 URL。
- 备份列表：同一标准台最多 3 条**不同** URL，按源 priority + 区域排序。VLC / PotPlayer 请只用主列表。

---

## 推荐播放器与订阅方式

| 播放器 | 主列表 | 备份列表 | EPG | 说明 |
|--------|--------|----------|-----|------|
| TiviMate | 必订 `live.m3u` | 可同时订 `live_backup.m3u` | 自动读 url-tvg，或手动填 fanmingming e.xml | 支持多源/故障转移 |
| APTV | 必订 | 可订 | 订阅设置里填 EPG 地址并开自动更新 | iOS / tvOS / macOS |
| TVBox / 影视仓 / 易播 | 必订 | 视壳子是否支持多链接 | 接口 EPG 字段或 url-tvg | 壳子能力不一 |
| Kodi PVR IPTV Simple | 必订 | 一般不订 | EPG URL 填 fanmingming e.xml | 专业但配置多 |
| VLC | 只订主列表 | 不要订备份 | 几乎无 EPG | 当直播源用 |
| PotPlayer | 只订主列表 | 不要订备份 | 需插件 | 当直播源用 |

主列表 vs 备份：主列表干净、一台一链，适合所有播放器；备份给「会自动换链」的客户端提高可用性，不会进默认订阅。

---

## 本地运行

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
pytest tests/ -q
python scripts/manage_sources.py validate
python scripts/collect.py
python scripts/verify_outputs.py
```

### 源管理示例

```bash
python scripts/manage_sources.py list
python scripts/manage_sources.py validate --online
python scripts/manage_sources.py disable ccsh-hotel
python scripts/manage_sources.py enable ccsh-hotel
python scripts/manage_sources.py stats
```

添加源见 [docs/ADD_SOURCE.md](docs/ADD_SOURCE.md)，禁用/删除见 [docs/REMOVE_SOURCE.md](docs/REMOVE_SOURCE.md)，往精选列表加台见 [docs/ADD_CHANNEL.md](docs/ADD_CHANNEL.md)。

本地生成裁剪版 EPG：

```bash
python scripts/fetch_epg.py
python scripts/verify_outputs.py
```

---

## EPG 节目指南使用方法

通用：本项目主列表已自动写入 `url-tvg="https://live.fanmingming.com/e.xml"`。支持从 M3U 读取该字段的播放器无需再填。不支持的，手动填同一地址。

当前阶段优先保证「能用、自动、稳定」。仓库另有裁剪版 [`output/guide.xml`](https://raw.githubusercontent.com/Hawaiine/Oasisic-IPTV/main/output/guide.xml)（只含标准表频道）。自建地址稳定后会切换 `url-tvg`。

### APTV（Apple TV / iOS / macOS）

1. 添加订阅（live.m3u）。
2. 订阅设置 →「EPG」或「节目单」地址栏，填 `https://live.fanmingming.com/e.xml`。
3. 开启「自动更新 EPG」。

### TiviMate（Android TV）

1. 播放列表 → 编辑列表 → EPG 源 → 添加。
2. 地址：`https://live.fanmingming.com/e.xml`。
3. 开启自动更新。

### TVBox / 影视仓 / 易播等

在直播源配置或接口的 EPG 字段填 `https://live.fanmingming.com/e.xml`。部分壳子会读 M3U 的 `url-tvg`，可先试是否自动生效。

### VLC

对 XMLTV 支持弱。需要节目单时改用 TiviMate / APTV。本列表仍可当直播源用。

### PotPlayer

选项里若有 IPTV/EPG 插件，手动指定 `https://live.fanmingming.com/e.xml`。多数情况下只当直播列表用。

### Kodi + PVR IPTV Simple Client

- M3U 播放列表：本项目 `live.m3u`
- EPG 抓取 URL：`https://live.fanmingming.com/e.xml`

### 其他 XMLTV 播放器

统一使用 `https://live.fanmingming.com/e.xml`。

---

## 命名规范

- 央视：`CCTV-1 综合`、`CCTV-5+ 体育赛事`、`CCTV-4K 超高清`。禁止 `CCTV1` / `CCTV1HD` / `CCTV-01`。
- 卫视：`湖南卫视`、`东方卫视`（不是「上海东方卫视」）、`东南卫视`（不是「福建东南卫视」）。禁止「高清」「HD」「卫视频道」。
- 全部简体；去掉分辨率、编码、运营商、IPV6、测试、备用标签。

---

## 项目结构

见 [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)。流水线见 [docs/PIPELINE.md](docs/PIPELINE.md)。

当前启用 **14** 个公开源（`config/sources.yaml`）。标准表 119 个实体。已剔除空列表源（ssili-tv）、与 zbds 重复的 vbskycn raw、低质国际源（Free-TV / iptv-org jp·kr）。酒店源降权保留。

---

## 数据源

源列表只维护在 `config/sources.yaml`。核心源连续失败会告警但不会自动禁用；非核心源连续 3 天失败自动 `enabled: false`。

---

## 声明

仅聚合公开链接，不托管媒体内容。使用者自行承担合规责任。
