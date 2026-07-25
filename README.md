# Oasisic-IPTV

📺 公开 IPTV 源日更聚合 · 分类 M3U · EPG · 可选地域测活

---

## 项目结构

```
Oasisic-IPTV/
├── config/
│   ├── sources.yaml       # 采集源配置
│   └── settings.yaml      # 全局设置
├── scripts/
│   ├── requirements.txt
│   └── lib/               # 采集/处理脚本（待开发）
├── output/                # 生成 M3U/EPG
├── data/                  # 数据缓存
├── docs/
│   ├── ARCHITECTURE.md    # 架构设计
│   ├── PIPELINE.md        # 数据流水线
│   └── RUNNER.md          # 自建 runner 部署
└── tests/
```

## 状态

🚧 **建设中** — 尚无采集逻辑，欢迎关注后续开发。

## 免责声明

本项目仅供学习研究用途。所有直播源链接来自公开互联网，版权归各自所有者所有。使用者应遵守当地法律法规，开发者不对使用后果承担责任。

## 许可证

MIT