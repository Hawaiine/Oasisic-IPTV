# 移除或禁用采集源

优先 **禁用**，不要轻易从 YAML 删除，方便回滚。

## 禁用（推荐）

```bash
python scripts/manage_sources.py disable fanmingming-ipv6   # 示例：换成目标 key
python scripts/manage_sources.py list
```

等价于把该源的 `enabled: true` 改成 `false`。下次 collect 会跳过。

重新启用：

```bash
python scripts/manage_sources.py enable fanmingming-ipv6
```

## 自动禁用

非核心源连续 `auto_disable_fail_days`（默认 3）天拉取失败，collect 会把 `enabled` 改为 `false`。  
核心源（`core: true`）只告警，不自动禁用。

历史在 `data/source_stats.json`：

```bash
python scripts/manage_sources.py stats
```

## 彻底删除

1. 先 `disable` 观察一两天。
2. 从 `config/sources.yaml` **只删该 key 那一整块**，不要动其他源。
3. `python scripts/manage_sources.py validate`
4. 更新 README 源数量。

不要 `git add -A`。白名单：`config/sources.yaml`、`README.md`、`CHANGELOG.md`。
