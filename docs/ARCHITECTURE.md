# Oasisic-IPTV 架构

公开 IPTV 源日更聚合工具。配置与代码分离，采集流水线无状态，不检测直播流是否可播放。

## 角色

| 路径 | 职责 |
|------|------|
| `config/sources.yaml` | 采集源唯一真实来源 |
| `config/settings.yaml` | 全局开关（一台一链、双列表、超时、严格模式） |
| `data/channels.json` | 标准频道表（standard_name + display_name + category + tvg_id；可选 priority / preferred_region） |
| `data/aliases.json` | 别名 → standard_name（禁止 orphan） |
| `data/cctv_programs.json` | 央视数字台 → 节目名（clean 加载，缺失回退内置） |
| `data/weishi_aliases.json` | 卫视别名统一映射（clean 加载，缺失回退内置） |
| `data/source_stats.json` | 每源成功/失败历史 |
| `scripts/collect.py` | 调度：拉源 → 解析 → 清洗 → 匹配 → 分类 → 选优 → 写出 |
| `scripts/lib/*` | 纯函数模块，无 IO 副作用（除 io_util） |
| `scripts/manage_sources.py` | 源生命周期 CLI |
| `output/` | 生成物。裁剪版 `guide.xml` 进 git；全量 xml / `guide.xml.gz` 不进 git |
| `scripts/fetch_epg.py` | 拉上游 EPG → 按 tvg_id 裁剪 → programme 去重 |

## 流水线

```
sources.yaml
    │  aiohttp 并发 GET
    ▼
parse M3U/TXT
    │  clean_channel_name（简体、去标签、央视/卫视规范）
    ▼
match  精确 → 别名 → 折叠模糊
    │  命中 = catalog 候选
    ▼
classify  表内用表分类；未命中走关键词回退
    │
    ▼
select  全局 URL 去重 → rtp 降权 → 区域/priority 排序 → max_keep=1
    │
    ├─ matched 且非电台非（可选）国际 → live.m3u（max_keep=1）+ live_{cat}.m3u
    ├─ 同口径标准台 最多 3 条 URL     → live_backup.m3u
    ├─ 其余保留                    → live_more.m3u
    └─ radio                       → live_radio.m3u

EPG（旁路，失败不挡 M3U）：
epg_sources → fetch_epg.py → 按 channels.json tvg_id 裁剪
    → output/guide.xml（进 git）+ guide.xml.gz（gitignore）
M3U 头：#EXTM3U url-tvg="https://live.fanmingming.com/e.xml"
```

## 选优维度

1. `rtp://` 降权（保留但不优先）
2. 区域：cn → hk_tw → hotel → overseas；频道 `preferred_region` 命中则该区域升至 cn 同级
3. 频道 `priority`（越小越优先，默认 50，先于源 priority）
4. 源 `priority`（越小越优先）
5. 已匹配标准表优先
6. 同 URL 全局去重：非电台赢

## 可观测性

阶段统计走 `logging`（统一前缀，INFO 级，单行摘要，不刷屏）：
- `[match]`：总频道数、精确/别名/模糊/未命中、命中率
- `[select]`：rtp 降权数、URL 去重数、选中数、各分类条数
- `[collect]`：live/backup/more/radio 终值及各分类条数

源健康检查：`manage_sources.py validate --online` 会解析内容，有效频道数 < 5 视为「空列表」异常——核心源仅告警，非核心源计入失败并建议禁用。

## 不做什么

- 不检测直播流 / TS / HLS 是否可播放
- 不上数据库、Web UI、复杂调度
- 不把 iptv-org 英文国家树当主 `group-title`
- 不 `git add -A`，不 force push
