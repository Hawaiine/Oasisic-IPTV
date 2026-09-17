# 贡献指南

## 提交流程

- 小修复直接 PR。
- 频道表扩容走 `scripts/suggest_channels.py --apply` 或手动改 `data/channels.json`；运行 `python scripts/sync_epg_ids.py` 更新 `epg_id`。
- 源治理改 `config/sources.yaml`，不要改 `scripts/lib/sources.py`。
- 分类兜底改 `scripts/lib/classify.py` 时，同步更新 `docs/CHANNEL_STANDARD.md` 的分类词表。

## 验证标准

- `pytest tests/ -q`
- `python scripts/manage_sources.py validate`
- `python scripts/collect.py`
- `python scripts/verify_outputs.py`
- `python scripts/fetch_epg.py`（如改动 EPG）

## Commit 规范

中英文均可，建议中文 + emoji。推荐前缀：

- `🎨` 样式/文档/非代码
- `🐛` bug 修复
- `✨` 新功能/新频道/新源
- `📦` 产物/输出变更
- `♻️` 重构
- `🧹` 清理/重命名
- `🌐` 镜像/CDN/网络
- `📝` 文档
- `🔖` 发布/版本
- `🔀` 合并/重排

示例：

- `🐛 修复 fetch_epg.py 多源合并漏掉第二个上游`
- `✨ 新增 CCTV-4K 超高清、CCTV-世界地理 等 7 个付费/数字频道`
- `📝 更新 README：guide.xml 已移出 git`

## 代码风格

- 4 空格缩进。
- 类型提示优先。
- 脚本放在 `scripts/` 或 `scripts/lib/`；测试放在 `tests/`。
- 不改动 `output/` 下的生成物；这些文件由流水线生成。
- 不在 `output/` 里提交 `guide.xml`。

## 提问

先看 [docs/FAQ.md](docs/FAQ.md)；仍不明确再开 Issue。