# Oasisic-IPTV

📺 公开 IPTV 源日更聚合 · 分类 M3U · EPG · 可选地域测活

---

## 项目结构

```
Oasisic-IPTV/
├── config/
│   ├── sources.yaml       # 采集源配置（约 20 个中文优先源）
│   └── settings.yaml      # 全局设置
├── scripts/
│   ├── collect.py         # 主采集管线
│   ├── manage_sources.py  # 源管理工具（validate / list）
│   ├── lib/               # 核心库
│   │   ├── categories.py  # 分类定义
│   │   ├── clean.py       # 频道名清洗
│   │   ├── m3u.py         # M3U 解析/生成
│   │   ├── match.py       # 标准表匹配
│   │   ├── io_util.py     # 文件 I/O 工具
│   │   └── probe.py       # 测活接口（stub，Phase5 完整实现）
│   └── requirements.txt
├── data/
│   ├── channels.json      # 标准频道表
│   └── aliases.json       # 频道别名字典
├── output/                # 生成 M3U/EPG
├── docs/
│   ├── ARCHITECTURE.md    # 架构设计
│   ├── PIPELINE.md        # 数据流水线
│   └── RUNNER.md          # 自建 runner 部署
└── tests/
```

## 状态

🚧 **建设中**

## 本地运行

```bash
# 安装依赖
python -m venv .venv
source .venv/bin/activate
pip install -r scripts/requirements.txt

# 运行测试
pytest -q

# 验证源配置
python scripts/manage_sources.py validate

# 列出源
python scripts/manage_sources.py list

# 执行采集（无测活）
PROBE_ENABLED=false python scripts/collect.py
```

## 数据流水线

```
采集 → 解析 → 清洗 → 匹配 → 分组 → 测活 → 选优 → 生成
```

详见 [docs/PIPELINE.md](docs/PIPELINE.md)。

## 免责声明

本项目仅供学习研究用途。所有直播源链接来自公开互联网，版权归各自所有者所有。使用者应遵守当地法律法规，开发者不对使用后果承担责任。

## 许可证

MIT