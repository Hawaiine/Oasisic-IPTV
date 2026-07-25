# Oasisic-IPTV 数据流水线

## 流程

```
采集 → 解析 → 清洗 → 匹配 → 分类 → 分组 → [可选测活] → 选优 → 生成
```

## 双 job 职责（probe 为可选增强）

### collect（云端，必跑）

- **职责**：候选/完整列表，**无测活**
- **步骤**：采集 → EPG → 报告 → 验证 → 提交日更
- **触发**：UTC 22:00 + workflow_dispatch
- **不依赖** self-hosted runner
- **STRICT**：核心源（cn/hk/tw + fanmingming + yuechan）须 100% 成功

### probe（自建 runner，可选）

- **职责**：测活 + `live_verified` + 失效源标记 + 可覆盖分类
- **镜像**：[oasisic-runner](https://github.com/Hawaiine/oasisic-runner)（`barryallen26/oasisic-runner`）
- **触发**：workflow_dispatch；collect 成功后的 workflow_run（可按需加 schedule）
- **runs-on**：`[self-hosted, iptv]`
- **无 runner**：请 Disable 本 workflow 或忽略 queued；**不影响 collect**
- **冲突**：`pull --rebase` 失败即 fail，禁止 force
- **口径**：测活结果 = runner 所在出口（如武汉联通），非全国通用

### 1. 采集 (Collect)

从 `config/sources.yaml` 拉取 M3U。核心源 100% 成功；国际补源失败仅警告。

### 2. 解析 (Parse)

提取频道名、tvg-id、logo、group-title。

### 3. 清洗 (Clean)

zhconv、去噪声标签、无效行。

### 4. 匹配 (Match)

标准表 + 别名。

### 5. 分类 (Classify)

标准表 → 关键词兜底 → other；写出前统一 `group_title`。

### 6. 分组 (Group)

央视→卫视→省市→港澳台→体育→直播→国际→酒店→其他；电台单独文件。

### 7. 测活 (Probe) — 可选

- 仅 self-hosted / 本地 `PROBE_ENABLED=true`
- m3u8 首段验证
- 产出 `live_verified.m3u`

### 8. 选优 (Select)

`max_keep_per_channel`；测活模式下仅保留 alive。

### 9. 生成 (Generate)

分类 M3U、check_result、CHANGELOG；EPG 默认不进 git（Artifact）。
