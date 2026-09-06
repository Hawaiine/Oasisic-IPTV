# 添加采集源

`config/sources.yaml` 是唯一真实来源。添加后下次 `collect` 自动生效，不用改 Python。

## 步骤

1. 确认 URL 返回 **HTTP 200**，且正文是 `#EXTM3U`（m3u）或 `名称,URL`（txt）。
2. 选一个全局唯一的 `key`（小写 + 短横线）。
3. 在 `sources:` 列表末尾追加：

```yaml
  - key: "example-cn"
    url: "https://example.com/live.m3u"
    type: "m3u"          # m3u | txt
    enabled: true
    region: cn           # cn | hk_tw | hotel | overseas | radio
    priority: 40         # 越小越优先
    core: false          # true = 连续失败只告警，不自动禁用
```

4. 校验：

```bash
python scripts/manage_sources.py validate
python scripts/manage_sources.py validate --online
```

5. 跑采集并看报告：

```bash
python scripts/collect.py
python scripts/verify_outputs.py
```

6. 同步 README「数据源」计数（以 `sources.yaml` 实际启用数为准）。

## 完整示例

新增一个 IPv6 中文源：

```yaml
  - key: "hujingguang-iptv"
    url: "https://raw.githubusercontent.com/hujingguang/ChinaIPTV/main/cn.m3u"
    type: "m3u"
    enabled: true
    region: cn
    priority: 45
    core: false
```

```bash
python scripts/manage_sources.py validate --online
python scripts/collect.py
```

## 注意

- 不要用 `iptv-org` 的 `index.m3u` / `playlist/cn.m3u`（易 404）。国家切片用 `https://iptv-org.github.io/iptv/countries/cn.m3u`。
- 一次只加 1–3 个源，先看成功率再加。
- 加源不会让主列表变整齐；主列表只收标准表命中。要「更多又整齐」请改 `data/channels.json`，见 [ADD_CHANNEL.md](ADD_CHANNEL.md)。
