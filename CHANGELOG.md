# 📺 工程日志

## 工程里程碑

| Phase | 日期 | 内容 |
|-------|------|------|
| Phase 0 | 2026-07-25 | 创建公开仓库骨架，目录结构，MIT 许可证 |
| Phase 1 | 2026-07-25 | 核心 lib（categories/clean/m3u/match/io_util/probe），标准表 + 别名字典，pytest 套件 |
| Phase 2 | 2026-07-25 | 无测活采集管线（collect.py），源管理工具（manage_sources.py），21 个源 |
| Phase 2.5 | 2026-07-25 | 源 URL 修正（iptv-org.github.io），关键词分类兜底（classify.py），STRICT 源门禁 |
| Phase 3 | 2026-07-25 | 输出验证（verify_outputs.py），Discord 通知（send_discord.py），每日 collect CI |
| Phase 4 | 2026-07-25 | EPG 多源合并（fetch_epg.py），工程报告（generate_report.py），group-title 收敛，日更提交收窄 |
| Phase 5 | 2026-07-25 | m3u8 子片段测活（probe.py），probe workflow，RUNNER 文档，STRICT 文档一致 |
| Phase 6 | 2026-07-25 | 失效源标记（flag_dead_sources.py），双 job 冲突硬化，workflow_run 门禁 |
| Phase 7 | 2026-07-25 | README / CHANGELOG 收尾，订阅链接与旧链清理 |
| 架构收口 | 2026-07-25 | 自研 [oasisic-runner](https://github.com/Hawaiine/oasisic-runner)；probe 改为可选增强；弃用 minimal-runner |

---

## 📺 采集报告 (2026-07-25 15:31:57)

- **状态**: stage=collect, total=19172, probe_enabled=False
- **生成时间**: 2026-07-25 15:30:48

### 📁 文件概览

| 文件 | 条数 |
|------|------|
| live.m3u | 18823 |
| live_cctv.m3u | 138 |
| live_gangtai.m3u | 36 |
| live_live.m3u | 10 |
| live_local.m3u | 109 |
| live_other.m3u | 15552 |
| live_overseas.m3u | 2853 |
| live_radio.m3u | 349 |
| live_sports.m3u | 41 |
| live_weishi.m3u | 84 |

### 🏷️ 分类分布 (live.m3u)

| 分类 | 条数 |
|------|------|
| 其他 | 15552 |
| 国际 | 2853 |
| 央视 | 138 |
| 各省市 | 109 |
| 卫视 | 84 |
| 体育 | 41 |
| 港澳台 | 36 |
| 网络直播 | 10 |

---

## 📺 采集报告 (2026-07-25 15:25:27)

- **状态**: stage=collect, total=19172, probe_enabled=False
- **生成时间**: 2026-07-25 15:25:06

### 📁 文件概览

| 文件 | 条数 |
|------|------|
| live.m3u | 18823 |
| live_cctv.m3u | 138 |
| live_gangtai.m3u | 36 |
| live_live.m3u | 10 |
| live_local.m3u | 109 |
| live_other.m3u | 15552 |
| live_overseas.m3u | 2853 |
| live_radio.m3u | 349 |
| live_sports.m3u | 41 |
| live_weishi.m3u | 84 |

### 🏷️ 分类分布 (live.m3u)

| 分类 | 条数 |
|------|------|
| 其他 | 15552 |
| 国际 | 2853 |
| 央视 | 138 |
| 各省市 | 109 |
| 卫视 | 84 |
| 体育 | 41 |
| 港澳台 | 36 |
| 网络直播 | 10 |

---

## 2026-07-25

### 📦 初始化 Oasisic-IPTV 仓库骨架

- 创建公开仓库 Hawaiine/Oasisic-IPTV
- 初始化目录结构（config/, scripts/, docs/, output/, data/, tests/）
- 配置 sources.yaml（3 个测试源）、settings.yaml
- 撰写架构文档（ARCHITECTURE.md, PIPELINE.md, RUNNER.md）
- 添加 MIT 许可证、.gitignore、.gitattributes
- **Phase 0 完成，尚无采集逻辑**