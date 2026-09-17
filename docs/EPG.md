# EPG（节目单）说明

本仓库的 `output/guide.xml` 是**多上游合并 + 按标准表裁剪**后的 XMLTV 节目单，只包含标准频道表里的台，
体积远小于上游全量（当前约 2.9 MB），可随 M3U 一起订阅。

## 1. 上游清单（`config/settings.yaml` → `epg_sources`）

| # | 上游 | id 体系 | 实测规模（2026-09-18） |
|---|------|---------|------------------------|
| 1 | `live.fanmingming.com/e.xml` | 央视 `CCTV1`、卫视中文名 | 124 频道 / 31107 programme |
| 2 | `raw.githubusercontent.com/fanmingming/live/main/e.xml` | 同上（与 #1 同源的镜像） | 同上（合并时自动去重） |
| 3 | `epg.112114.xyz/pp.xml` | 混合（`CCTV10`… + 中文名） | 504 频道 / 16368 programme |
| 4 | `epg.pw/xmltv/epg_CN.xml` | **纯数字 id** | 669 频道 / 28594 programme（622 个有节目单） |

> 上游只维护在 `settings.yaml` 一处；新增上游后跑一次 `scripts/epg_inventory.py` 看它能覆盖多少再决定是否保留。
> 上游是「输入」，不是承诺：任何外部源都可能变更或消失，失败会被逐条打印，不会静默。

## 2. id 对齐规则（`epg_id`）

`data/channels.json` 的每个频道有两个 id，职责分离：

| 字段 | 用途 | 例 |
|------|------|----|
| `tvg_id` | 台标文件名、历史 id、回退值 | `HunanTV` |
| `epg_id` | 输出到 `#EXTINF` 的 `tvg-id`，用于对节目单 | `湖南卫视` |

匹配顺序（`scripts/lib/epg_map.py::choose_epg_id`）：

1. **id 直配**：`tvg_id` → `display_name` → `standard_name` → `aliases.json` 别名，取第一个在上游「有节目单」的；
2. **名字直配**：上游 id 是数字时（epg.pw 等），用 display-name 反查 id；
3. 都没命中 → `epg_id: null`，并写入 `data/epg_missing.txt`（原因分 `upstream-missing` / `upstream-no-programme`）。

硬规则：**只接受上游真实存在且有 programme 的 id**，禁止臆造、禁止用近似频道顶替。
输出 M3U 时 `tvg-id = epg_id or tvg_id`（由 `settings.use_epg_id` 控制），因此没有 EPG 的频道也不会退化。

## 3. 合并与裁剪（`scripts/fetch_epg.py`）

- **真合并**：所有成功上游都参与（历史实现会在第一个成功源后 `break`，导致第 2 个源永远不生效——已修）。
- 合并顺序 = `epg_sources` 顺序；`channel` 先到先得，`programme` 按 `(channel, start, stop)` 去重。
- 裁剪白名单 = 标准表的 `epg_id ∪ tvg_id`（`load_epg_ids()`）。
- 结束后打印每源贡献与总覆盖率（覆盖率同时是 `verify_outputs.py` 的硬检查项）。

## 4. 覆盖率现状

| 分类 | 覆盖 | 说明 |
|------|------|------|
| 央视 cctv | 26/26 | 含 CCTV-5+、CCTV-4K/8K、CGTN 系、CETV-1~4 |
| 卫视 weishi | 35/35 | 上游以中文名 id 提供，全量覆盖 |
| 各省市 local | 22/33 | 省会台多数有；广东/上海/武汉/成都/陕西部分频道上游缺失 |
| 港澳台 gangtai | 3/19 | 上游只提供 翡翠台/凤凰中文/凤凰资讯；其余 16 个上游没有节目单 |
| 体育 sports | 3/6 | 北京体育休闲、劲爆体育、高尔夫网球有；五星/广东体育/纬来无 |
| 网络直播 live | 1/1 | |
| **合计** | **90/120 = 75%** | 修前为 20/120 = 17% |

未覆盖的 30 个台逐条写在 `data/epg_missing.txt`（含原因），不隐藏、不糊弄。

## 5. 客户端怎么填

| 客户端 | EPG 地址 | 说明 |
|--------|----------|------|
| 通用（推荐） | `https://cdn.jsdelivr.net/gh/Hawaiine/Oasisic-IPTV@main/output/guide.xml` | 覆盖 90 个台，与 M3U 的 `tvg-id` 完全对应 |
| 备选 | `https://raw.githubusercontent.com/Hawaiine/Oasisic-IPTV/main/output/guide.xml` | jsDelivr 不可达时用 |
| 不用本仓库 | `https://live.fanmingming.com/e.xml` | 只覆盖上游那部分（中文名 id 的卫视 + CCTV），港澳台/地方台仍缺 |

M3U 头部的 `url-tvg` 目前仍指向上游地址；**切换到自建 guide.xml 需要先在目标客户端实测通过**再改
（未实测不改，见下节结论）。

## 6. 频道编号（`tvg-chno`）：本期不启用

实测依据（2026-09-18 检索）：

- **TiviMate**：社区明确「不支持 `tvg-chno`，短期无计划」，它按 M3U 里的顺序自动编号；
- **Kodi PVR IPTV Simple**：官方 wiki 列出 `tvg-chno`，但新版 addon 说明写明「忽略 `tvg-chno`，只按 M3U 顺序编号」——支持面不稳定；
- **APTV**：未见可靠证据支持该字段。

结论：不写 `tvg-chno`。等价效果由**列表顺序**承担——`live.m3u` 已按 央视 → 卫视 → 各省市 → 港澳台 → 体育 → 网络直播 分组排序，
客户端按顺序编号即可得到稳定台号。

## 7. 维护操作

```bash
# 盘点上游（只读，输出 output/epg_inventory.json + 终端摘要）
python scripts/epg_inventory.py

# 重新对齐 epg_id 并刷新缺口清单（幂等：无变化时 0 改动）
python scripts/sync_epg_ids.py
python scripts/sync_epg_ids.py --check      # 只校验覆盖率是否达标

# 生成裁剪版节目单 + 覆盖率报告
python scripts/fetch_epg.py

# 全量校验（含 EPG 覆盖率硬检查）
python scripts/verify_outputs.py
```

阈值与开关（`config/settings.yaml`）：`epg_min_coverage`（低于则 CI 失败）、`use_epg_id`（是否用 epg_id 输出）。

## 8. 常见问题

- **某台没有节目单**：先看 `data/epg_missing.txt` 的原因；若原因是 `upstream-missing`，是本仓库上游确实没有，不是 bug。
- **加了新台但没 EPG**：跑 `sync_epg_ids.py` 后它会被自动对齐或进缺口清单；上游后续补充节目单时，重跑即自动命中。
- **覆盖率掉到阈值以下**：`verify_outputs.py` 会失败并打印分类明细；通常是某个上游挂了，看 `fetch_epg.py` 的逐源输出定位。
- **guide.xml 体积**：当前约 2.9 MB（每天随日更提交）。如果在意仓库体积，可在后续阶段改为发布到 Release/Pages 或只保留若干天窗口。