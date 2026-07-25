# Oasisic-IPTV 架构设计

## 架构概览

```
                     ┌──────────────────┐
                     │   GitHub Cloud   │
                     │  collect.yml     │  ◄── 必跑日更
                     │   UTC 22:00      │
                     └──────┬───────────┘
                            │ live.m3u / 分类 / artifact
                            ▼
                     ┌──────┴──────┐
                     │   main 仓   │
                     └──────┬──────┘
                            │ 可选
                            ▼
                     ┌──────┴──────────┐
                     │ oasisic-runner  │  self-hosted,iptv
                     │ (如武汉联通)    │
                     │ probe.yml       │
                     └──────┬──────────┘
                            │ 有则推 live_verified
                            ▼
                     ┌──────┴──────┐
                     │   main 仓   │
                     └─────────────┘
```

## 关键决策

### 云端必跑 + 测活可选

- **collect**：纯采集，不测活，保证公开列表日更
- **probe**：可选；依赖 [oasisic-runner](https://github.com/Hawaiine/oasisic-runner)
- 无 runner 时 Disable `probe` workflow 即可，主链路不受影响

### 测活口径

- 等于 **runner 所在出口**（部署在武汉联通则写武汉联通）
- 方式：HTTP + m3u8 首段验证
- **禁止**写成全国/全球可用

### 家宽说明

- IPv4 无公网仍可跑 runner（出站即可）
- IPv6 有公网可覆盖部分源
