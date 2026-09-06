# 采集流水线

本地一次完整运行：

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pytest tests/ -q
python scripts/manage_sources.py validate
python scripts/collect.py
python scripts/verify_outputs.py
python scripts/fetch_epg.py          # 裁剪版 output/guide.xml（进 git）
python scripts/generate_report.py
```

可选：

```bash
python scripts/send_discord.py       # 需要环境变量 DISCORD_WEBHOOK
```

## 步骤说明

| 步 | 模块 | 失败策略 |
|----|------|----------|
| 拉源 | `collect.fetch_all` | 单源失败记日志，继续 |
| 解析 | `lib.m3u` | 空列表视为该源失败 |
| 清洗 | `lib.clean` | 空名丢弃 |
| 匹配 | `lib.match` | 未命中进 more，不丢 |
| 分类 | `lib.classify` | 未知 → 其他 |
| 选优 | `lib.select` | 一台一链 |
| 校验 | `verify_outputs.py` | 失败则非 0 退出 |
| 严格模式 | `strict_sources_ratio` | 启用源成功率 < 70% 或核心源全失败 → CI 失败 |
| EPG | `fetch_epg.py` | 失败 Discord 告警，CI 仍绿 |

时区一律 `Asia/Shanghai`，`check_result.generated_at` 格式 `YYYY-MM-DD HH:MM:SS`。
