## 这个 PR 做了什么

<!-- 一两句话。涉及源/频道请贴上证据（状态码、首行、条数）。 -->

## 自查（合并前必须全绿）

- [ ] `pytest tests/ -q` 通过
- [ ] `python scripts/manage_sources.py validate` 通过
- [ ] `STRICT_SOURCES=0 python scripts/collect.py` 跑通
- [ ] `python scripts/verify_outputs.py` 全部通过
- [ ] PR 的 `pr-verify` workflow 绿了（自动跑上面四步）
- [ ] 没有提交 `output/` 下的日更产物（除新增格式首次落地）
- [ ] 没有把密钥/Webhook 写进仓库

## 影响面

- [ ] 改了 `config/sources.yaml`（新增/禁用源）
- [ ] 改了 `data/channels.json` / `aliases.json`（标准表）
- [ ] 改了清洗/匹配/选优逻辑（需要补测试）
- [ ] 改了 workflow
- [ ] 只改文档
