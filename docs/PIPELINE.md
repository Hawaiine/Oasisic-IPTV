# Oasisic-IPTV 数据流水线

## 流程

```
采集 → 清洗 → 匹配 → 分组 → 测活 → 选优 → 生成
```

### 1. 采集 (Collect)
从 `config/sources.yaml` 中配置的源 URL 拉取 playlists/CSV/index。

### 2. 清洗 (Clean)
- 去除空行、注释行、无效 URL
- 标准化编码（zhconv 繁转简）
- 去除分辨率标签、状态标记等噪声

### 3. 匹配 (Match)
将频道名匹配到标准频道表（`channels.json`），利用别名字典（`aliases.json`）提高匹配率。

### 4. 分组 (Classify)
按类别分组：
- 央视 → 卫视 → 各省市 → 港澳台 → 体育 → 网络直播 → 国际 → 电台 → 其他

### 5. 测活 (Probe)
- 仅 self-hosted runner 执行
- HTTP HEAD 快速过滤 + m3u8 子片段验证
- 武汉联通出口

### 6. 选优 (Select)
- 每频道最多保留 `max_keep_per_channel` 个源
- 优先：存活时间 > 响应速度 > 分辨率

### 7. 生成 (Generate)
- 输出分类 M3U 文件
- 合并 EPG（多源 XML）
- 生成 CHANGELOG 报告