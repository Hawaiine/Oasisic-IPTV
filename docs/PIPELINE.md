# Oasisic-IPTV 数据流水线

## 流程

```
采集 → 解析 → 清洗 → 匹配 → 分类 → 分组 → 测活 → 选优 → 生成
```

## 双 job 职责

### collect（云端，GitHub ubuntu-latest）
- **职责**：候选/完整列表采集，无测活
- **步骤**：采集 → EPG → 报告 → 验证 → 提交日更
- **触发**：UTC 22:00 定时 + workflow_dispatch
- **不依赖** self-hosted runner，任何时刻独立运行
- **STRICT 源策略**：核心源（cn/hk/tw + fanmingming + yuechan）必须 100% 成功

### probe（自建 runner，武汉联通出口）
- **职责**：测活 + live_verified + 失效源标记 + 可覆盖分类文件
- **步骤**：采集 → 测活 → 失效标记 → 验证 → 报告 → 提交
- **触发**：collect 成功后的 workflow_run + UTC 22:30 定时 + workflow_dispatch
- **网络口径**：武汉联通，IPv4 NAT（仅出站），IPv6 有公网
- **冲突处理**：pull --rebase 失败时 job 立即 fail，禁止 force push
- **离线说明**：runner 离线时 job 失败/queued，不影响 collect 已推内容

### 1. 采集 (Collect)
从 `config/sources.yaml` 中配置的源 URL 拉取 M3U 播放列表。

**源策略：** 核心源（cn/hk/tw + fanmingming + yuechan）要求 100% 成功率；
国际补源失败仅警告，不阻塞整 job。总成功率不设阈值（仅卡核心源）。

### 2. 解析 (Parse)
解析 M3U 格式，提取频道名、tvg-id、tvg-logo、group-title。

### 3. 清洗 (Clean)
- 去除空行、注释行、无效 URL
- 标准化编码（zhconv 繁转简）
- 去除分辨率标签、状态标记等噪声

### 4. 匹配 (Match)
将频道名匹配到标准频道表（`channels.json`），利用别名字典（`aliases.json`）提高匹配率。

### 5. 分类 (Classify)
优先级：
1. 标准表匹配命中 → 直接使用其 category
2. 关键词/规则兜底（央视/CCTV、卫视、港澳台、体育、电台等）
3. 其余 → other

写入 M3U 前统一 **group_title = categories.group_title(category)**，禁止源侧杂名。

### 6. 分组 (Group)
按类别分组：
- 央视 → 卫视 → 各省市 → 港澳台 → 体育 → 网络直播 → 国际 → 特殊·酒店源 → 其他
- 电台单独，不进 live.m3u

### 7. 测活 (Probe)
- 仅 self-hosted runner 执行
- HTTP HEAD 快速过滤 + m3u8 子片段验证
- 武汉联通出口

### 8. 选优 (Select)
- 每频道最多保留 `max_keep_per_channel` 个源
- 优先：存活时间 > 响应速度 > 分辨率

### 9. 生成 (Generate)
- 输出分类 M3U 文件（live.m3u + 各分类文件）
- 合并 EPG（多源 XML，输出 guide.xml）
- 生成 CHANGELOG 工程报告