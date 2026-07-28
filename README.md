# Oasisic-IPTV 📺

[![collect](https://github.com/Hawaiine/Oasisic-IPTV/actions/workflows/collect.yml/badge.svg)](https://github.com/Hawaiine/Oasisic-IPTV/actions/workflows/collect.yml)
[![License](https://img.shields.io/github/license/Hawaiine/Oasisic-IPTV)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.11+-blue)](https://www.python.org/)
[![更新频率](https://img.shields.io/badge/更新-每日UTC22:00-brightgreen)]()

公开 IPTV 源日更聚合 — 分类 M3U · EPG · 可选地域测活（武汉联通出口）。

---

## 订阅链接

> 所有链接均为 `raw.githubusercontent.com` 直链，可直接用于播放器（VLC / PotPlayer / Kodi 等）。

| 文件 | 链接 | 说明 |
|------|------|------|
| **完整列表** | [`live.m3u`](https://raw.githubusercontent.com/Hawaiine/Oasisic-IPTV/main/output/live.m3u) | 所有分类合并 |
| 央视 | [`live_cctv.m3u`](https://raw.githubusercontent.com/Hawaiine/Oasisic-IPTV/main/output/live_cctv.m3u) | CCTV 频道 |
| 卫视 | [`live_weishi.m3u`](https://raw.githubusercontent.com/Hawaiine/Oasisic-IPTV/main/output/live_weishi.m3u) | 卫星电视 |
| 各省市 | [`live_local.m3u`](https://raw.githubusercontent.com/Hawaiine/Oasisic-IPTV/main/output/live_local.m3u) | 地方频道 |
| 港澳台 | [`live_gangtai.m3u`](https://raw.githubusercontent.com/Hawaiine/Oasisic-IPTV/main/output/live_gangtai.m3u) | 香港/澳门/台湾 |
| 体育 | [`live_sports.m3u`](https://raw.githubusercontent.com/Hawaiine/Oasisic-IPTV/main/output/live_sports.m3u) | 体育频道 |
| 网络直播 | [`live_live.m3u`](https://raw.githubusercontent.com/Hawaiine/Oasisic-IPTV/main/output/live_live.m3u) | 斗鱼/虎牙/B站 |
| 国际 | [`live_overseas.m3u`](https://raw.githubusercontent.com/Hawaiine/Oasisic-IPTV/main/output/live_overseas.m3u) | 国际频道 |
| 特殊·酒店源 | `live_special.m3u` | 酒店/特殊源 |
| 电台 | [`live_radio.m3u`](https://raw.githubusercontent.com/Hawaiine/Oasisic-IPTV/main/output/live_radio.m3u) | 广播电台 |
| **测活通过** | `live_verified.m3u` | 武汉联通出口视角，非全国通用 |

**EPG 节目指南：** 默认不进 git 仓库。从 [Actions Artifact](https://github.com/Hawaiine/Oasisic-IPTV/actions/workflows/collect.yml) 下载 `oasisic-iptv-output` 获取 `guide.xml`。

---

## 可播口径说明

| 列表 | 含义 |
|------|------|
| `live.m3u` / 分类 `live_*.m3u` | **候选聚合** — 自动采集、清洗、去重后的公开 IPTV 源集合，按中文分类组织。未经过本仓库测活验证，不代表所有链接均可播放。 |
| `live_verified.m3u` | **武汉联通出口测活子集** — 仅当 self-hosted runner（武汉联通 AS4837）在线时生成，代表该出口视角下可连通的流。**非全国通用，不代表其他地域/运营商可用。** |
| `live_radio.m3u` | 电台专列，独立文件，不混入主列表。 |
| `live_overseas.m3u` | 国际频道（默认不加入主列表，通过 `main_include_overseas` 配置）。 |

> 本仓库收录 ≠ 本仓库保证可播。地域性（组播/内网/酒店 auth）源在候选列表中保留，但测活视角仅限武汉联通出口。没有 runner 时 probe workflow 保持 Disabled，不伪造测活结果。

---

## 特性

- ✅ 每日 UTC 22:00 自动采集（GitHub Actions 云端）
- ✅ 15 个中文优先稳定源（iptv-org / fanmingming / YueChan / Free-TV）
- ✅ 标准频道表匹配 + 关键词分类兜底（9 大分类 + 电台）
- ✅ 频道名自动清洗（繁转简、去分辨率标签、CCTV 归一）
- ✅ **可选地域测活**：自建 [oasisic-runner](https://github.com/Hawaiine/oasisic-runner) 时产出 `live_verified`（无 runner 可跳过）
- ✅ 失效源自动标记（连续 3 天不可用 → 禁用；需测活数据）
- ✅ EPG 多源合并（guide.xml）
- ✅ 源管理工具（validate / list / disabled）
- ✅ 输出验证 + Discord 通知

---

## 项目结构

```
Oasisic-IPTV/
├── config/
│   ├── sources.yaml       # 采集源配置
│   └── settings.yaml      # 全局设置
├── scripts/
│   ├── collect.py         # 主采集管线
│   ├── manage_sources.py  # 源管理工具
│   ├── fetch_epg.py       # EPG 合并
│   ├── flag_dead_sources.py # 失效源标记
│   ├── generate_report.py # 采集报告生成
│   ├── send_discord.py    # Discord 通知
│   ├── verify_outputs.py  # 输出验证
│   └── lib/               # 核心库
│       ├── categories.py
│       ├── classify.py
│       ├── clean.py
│       ├── m3u.py
│       ├── match.py
│       ├── io_util.py
│       └── probe.py
├── data/
│   ├── channels.json      # 标准频道表
│   └── aliases.json       # 别名字典
├── output/                # 生成 M3U / EPG / check_result
├── .github/workflows/
│   ├── collect.yml        # 每日采集（云端，必跑）
│   └── probe.yml          # 测活（可选；无 runner 可禁用）
└── docs/
    ├── ARCHITECTURE.md    # 架构设计
    ├── PIPELINE.md        # 数据流水线 + 双 job 职责
    └── RUNNER.md          # 可选 oasisic-runner 部署
```

---

## 本地运行

```bash
# 环境
python -m venv .venv
source .venv/bin/activate
pip install -r scripts/requirements.txt

# 测试
pytest -q

# 管理源
python scripts/manage_sources.py validate
python scripts/manage_sources.py list
python scripts/manage_sources.py disabled

# 采集（无测活）
PROBE_ENABLED=false python scripts/collect.py

# 采集 + 测活（需本地网络环境）
PROBE_ENABLED=true PROBE_CONCURRENCY=5 python scripts/collect.py

# 验证输出
python scripts/verify_outputs.py

# EPG
python scripts/fetch_epg.py

# 失效源标记（需 probe 模式数据）
DRY_RUN=true python scripts/flag_dead_sources.py
```

---

## CI/CD

### collect（云端）
- **运行环境**：`ubuntu-latest`（GitHub Actions）
- **触发**：UTC 22:00 定时 + `workflow_dispatch`
- **步骤**：采集 → EPG → 报告 → 验证 → 提交日更 → Discord 通知
- **不依赖** self-hosted runner，任何时候独立运行

### probe（可选增强）
- **运行环境**：`[self-hosted, iptv]`（需部署 [oasisic-runner](https://github.com/Hawaiine/oasisic-runner)）
- **默认**：可在 Actions 中 **Disable**；无 runner 时不影响 `live.m3u` 日更
- **有 runner 时**：测活 → `live_verified.m3u` → 可选失效源标记
- **口径**：测活结果 = runner 所在出口（如武汉联通），**非全国通用**

### 部署可选 Runner

```bash
docker run -d --restart unless-stopped --name oasisic-runner \
  -e REPO_URL=https://github.com/Hawaiine/Oasisic-IPTV \
  -e ACCESS_TOKEN=ghp_your_token \
  -e RUNNER_NAME=oasisic-iptv-wuhan \
  -e RUNNER_LABELS=self-hosted,iptv,region-wuhan \
  ghcr.io/hawaiine/oasisic-runner:latest
```

或 Docker Hub（若已双推）：`barryallen26/oasisic-runner:latest`  
一键脚本：`curl -fsSL https://raw.githubusercontent.com/Hawaiine/oasisic-runner/main/install.sh | bash`（需先 `export ACCESS_TOKEN=...`）

镜像仓库与说明见 [Hawaiine/oasisic-runner](https://github.com/Hawaiine/oasisic-runner) 与 [docs/RUNNER.md](docs/RUNNER.md)。  
旧 `minimal-runner` 已弃用，请勿再使用。

---

## 相关项目

- [oasisic-runner](https://github.com/Hawaiine/oasisic-runner) — 可选自建 Actions Runner 镜像
- [Oasisic-Icons](https://github.com/Hawaiine/Oasisic-Icons) — 品牌图标库
- [mihomo-rules](https://github.com/Hawaiine/mihomo-rules) — 代理规则集
- [Oasisic-OpenWrt](https://github.com/Hawaiine/Oasisic-OpenWrt) — 固件编译
---

## 免责声明

本项目仅供学习研究用途。所有直播源链接来自公开互联网，版权归各自所有者所有。使用者应遵守当地法律法规，开发者不对使用后果承担责任。

## 许可证

MIT