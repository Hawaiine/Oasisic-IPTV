# Oasisic-IPTV

[![collect](https://github.com/Hawaiine/Oasisic-IPTV/actions/workflows/collect.yml/badge.svg)](https://github.com/Hawaiine/Oasisic-IPTV/actions/workflows/collect.yml)
[![License](https://img.shields.io/github/license/Hawaiine/Oasisic-IPTV)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.11+-blue)](https://www.python.org/)

公开 IPTV 源日更聚合工具 —— 多源采集、智能清洗、标准命名、目录制选优，生成干净可用的分类 M3U 播放列表。

Oasisic-IPTV 面向中文用户。它每日从多个公开源采集频道，经过名称清洗、标准频道表匹配、中文分类和一台一链选优后，输出结构清晰的 M3U，可导入 VLC、PotPlayer、TVBox、TiviMate、Kodi。

项目坚持目录制：主列表 `live.m3u` 只保留命中标准表的频道，且每台一条最优链接；`live_backup.m3u` 为同一批标准台保留最多 3 条不同 URL（给会自动切换的播放器）；扩展列表 `live_more.m3u` 保留未入表频道。源的新增、禁用、连续失败自动下线都走配置，不必改代码。

**不检测直播流是否可播放。** 收录不代表实时可播，请遵守当地法律法规。

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
| [`live_special.m3u`](https://raw.githubusercontent.com/Hawaiine/Oasisic-IPTV/main/output/live_special.m3u) | 酒店（目录制下通常为空，非推荐） |
| [`live_other.m3u`](https://raw.githubusercontent.com/Hawaiine/Oasisic-IPTV/main/output/live_other.m3u) | 其他（通常为空，非推荐） |
| [`live_radio.m3u`](https://raw.githubusercontent.com/Hawaiine/Oasisic-IPTV/main/output/live_radio.m3u) | 电台（独立文件） |
| [`guide.xml`](https://raw.githubusercontent.com/Hawaiine/Oasisic-IPTV/main/output/guide.xml) | 多上游合并裁剪的 EPG（当前覆盖 90/120 个标准台） |

主列表 `#EXTM3U` 已写入 `url-tvg="https://live.fanmingming.com/e.xml"`。台标已改为本仓库 `logo/` 托管，示例：`https://cdn.jsdelivr.net/gh/Hawaiine/Oasisic-IPTV@main/logo/CCTV1.png`。缺失台标列表见 `data/logo_missing.txt`（含已尝试的上游与结果）。

节目单（EPG）由**多个上游合并后按标准表裁剪**生成，覆盖 90/120 个台（卫视、央视全覆盖），详见 [docs/EPG.md](docs/EPG.md)。
想要更全的节目单，EPG 地址填本仓库的 `guide.xml`：`https://cdn.jsdelivr.net/gh/Hawaiine/Oasisic-IPTV@main/output/guide.xml`（jsDelivr 不通时用 raw 地址）。

国内访问 GitHub raw 慢时，主列表可用镜像：

- 原始：`https://raw.githubusercontent.com/Hawaiine/Oasisic-IPTV/main/output/live.m3u`
- jsDelivr：`https://cdn.jsdelivr.net/gh/Hawaiine/Oasisic-IPTV@main/output/live.m3u`
- ghproxy：`https://ghproxy.com/https://raw.githubusercontent.com/Hawaiine/Oasisic-IPTV/main/output/live.m3u`

普通用户只订 `live.m3u`；TiviMate / APTV 等支持多链接的可再订 `live_backup.m3u`。

---

## 可播口径

- **收录 ≠ 可播。** 列表只保证「公开源里出现过、经过清洗和选优」。
- **探活（可选）**：`scripts/probe.py` 可在**本机网络**实测每条链接能否拉到首片，结果写 `output/health.json`；
  本机跑完 `collect.py` 后，选优会按「本机实测可达性」优先排序（可播排前、死链降权、网络锁降权）。
  没有 `health.json` 或数据过期时，排序与旧版完全一致。
- **探活结果只代表探测出口网络**：家里跑 ≈ 你家能不能看；云端 CI 跑的是美国出口，**不代表大陆可用**。
  分级表、出口说明与用法见 [docs/PLAYABILITY.md](docs/PLAYABILITY.md)。
- 地域源、IPv6、酒店源、`rtp://` 组播可以收录；`rtp://` 会降权排后。
- 国际频道默认只出现在 `live_overseas.m3u` / `live_more.m3u`。
- 主列表一台一链：同一频道名最多 1 条 URL。
- 备份列表：同一标准台最多 3 条**不同** URL，按源 priority + 区域排序。VLC / PotPlayer 请只用主列表。
- 探活按链路类型另出三份**本机产物**（默认不进仓库）：`live_ipv6.m3u`（仅 IPv6 可播）、
  `live_cmcc.m3u`（403 网络锁，以移动魔百和为主）、`live_signed.m3u`（时效签名链接，会过期）。

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

# 可选：本机探活（按「本机能不能播」重排选优；结果写 output/health.json）
python scripts/probe.py --egress-label wuhan-unicom
python scripts/collect.py          # 再跑一次，读健康度重排
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

仓库另有多上游合并裁剪版 [`output/guide.xml`](https://raw.githubusercontent.com/Hawaiine/Oasisic-IPTV/main/output/guide.xml)（只含标准表频道，覆盖 90/120 个台，卫视与央视全覆盖）。**想要更全的节目单就填它**：
`https://cdn.jsdelivr.net/gh/Hawaiine/Oasisic-IPTV@main/output/guide.xml`。`tvg-id` 与标准表 `epg_id` 完全对应；没有 EPG 的台见 `data/epg_missing.txt`。上游清单、对齐规则与覆盖率表见 [docs/EPG.md](docs/EPG.md)。

> 频道编号：`tvg-chno` 目前**不写**（TiviMate 不支持、Kodi 新版忽略该字段）。台号由列表顺序决定，主列表已按 央视 → 卫视 → 各省市 → 港澳台 → 体育 → 网络直播 排好。

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

- 央视：`CCTV-1 综合`、`CCTV-5+ 体育赛事`、`CCTV-4K 超高清`、`CCTV-世界地理`（付费/数字频道同形）。禁止 `CCTV1` / `CCTV1HD` / `CCTV-01`。
- 卫视：`湖南卫视`、`东方卫视`（不是「上海东方卫视」）、`东南卫视`（不是「福建东南卫视」）。禁止「高清」「HD」「卫视频道」。
- 各省市：城市在前，如 `武汉新闻综合`、`河南民生`、`广州影视`。
- 全部简体；去掉分辨率、编码、运营商、IPV6、测试、备用标签。

完整字段规范、收录判据、黑名单与「怎么加台」见 [docs/CHANNEL_STANDARD.md](docs/CHANNEL_STANDARD.md)。

---

## 项目结构

见 [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)。流水线见 [docs/PIPELINE.md](docs/PIPELINE.md)。EPG（上游、对齐规则、覆盖率）见 [docs/EPG.md](docs/EPG.md)。可播性与探活见 [docs/PLAYABILITY.md](docs/PLAYABILITY.md)。频道标准与收录规则见 [docs/CHANNEL_STANDARD.md](docs/CHANNEL_STANDARD.md)。

当前启用 **28** 个公开源（`config/sources.yaml`），另有 4 个暂时禁用（见该文件注释）。标准表 **257** 个实体（央视 39 / 卫视 38 / 各省市 145 / 港澳台 19 / 体育 15 / 网络直播 1），其中 **227 个有 EPG（88.3%）**。fanmingming 是核心源之一（GitHub raw），不是唯一依赖。已剔除空列表源（ssili-tv）、与 zbds 重复的 vbskycn raw、低质国际源（Free-TV / iptv-org jp·kr）。酒店源降权保留。新增源来自社区评价较高的公开项目（joevess、mymsnn、zilong、CCSH、cs3306、TianmuTNT、zhi35、wwb521、Ftindy、BigBigGrandG、qwerttvv 等）。

名称黑名单（`config/exclude.yaml`）过滤点播回看、购物、测试、引流等非直播噪声；未命中标准表的条目走关键词分类兜底（`scripts/lib/classify.py`），分类不了的留在 `live_more.m3u` 的「其他」里，**不乱分**。扩容用 `scripts/suggest_channels.py`（从长尾里挑「有上游 EPG」的候选），台标用 `scripts/fetch_missing_logos.py` 补。

> IPv6 源（fanmingming-ipv6 等）频道更全；IPv4 用户建议同时订阅 `live_backup.m3u` 提高可用性。

---

## 日更与手动触发

- GitHub Actions 每天 **北京时间约 06:00**（cron `0 22 * * *` UTC）自动采集。
- 也可在 [Actions → collect](https://github.com/Hawaiine/Oasisic-IPTV/actions/workflows/collect.yml) 点 **Run workflow** 手动触发。
- 日更提交信息形如 `📺 每日采集 YYYY-MM-DD HH:MM`。EPG 拉取失败只告警，不阻断 M3U 更新。

---

## 数据源

源列表只维护在 `config/sources.yaml`。核心源连续失败会告警但不会自动禁用；非核心源连续 3 天失败自动 `enabled: false`。空壳列表 `live_other.m3u` / `live_overseas.m3u` / `live_special.m3u` 不再提交到仓库，**不推荐订阅**。

EPG 上游只维护在 `config/settings.yaml` 的 `epg_sources`（多个源真合并、按标准表裁剪）；对齐规则与当前覆盖率见 [docs/EPG.md](docs/EPG.md)。

---

## 声明

仅聚合公开链接，不托管媒体内容。使用者自行承担合规责任。
