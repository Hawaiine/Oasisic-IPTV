# 可播口径与探活（PLAYABILITY）

本仓库**不保证任何链接实时可播**。但「收录 ≠ 可播」之外，本项目提供一层**本机探活**能力，
让选优在有能力时按「本机真实可达性」排序，而不是只看源优先级。

## 1. 探活是什么

`scripts/probe.py` 对本机列表里的每个 URL 做一次**只读首片**的探测：

- 发 `Range: bytes=0-2047` 请求，不下载整段流、不建立长时间连接；
- 200/206 且首片像播放列表（含 `#EXTM3U`/`#EXTINF`）或像 MPEG-TS（`0x47` 同步字节）→ 记为可播；
- 若返回 200 但不是播放列表且配置允许，会**下探第一个分片**再判一次；
- 结果写 `output/health.json`，并按链路类型生成分列文件。

## 2. 分级表

| level | 含义 | 选优权重 | 说明 |
|-------|------|----------|------|
| `ok` | 首片可播 | 最高 | 主列表优先选它 |
| `playlist-missing` | 200 但响应体不是播放列表（含下探分片后仍失败） | 次之 | 多为套壳页面/中转脚本 |
| `timeout` | 超时 | 中 | 慢但可能可播，降权不淘汰 |
| `http-error` | 其他 4xx/5xx | 中 | |
| `unknown` | 未探测 / 数据过期 | 中（不奖惩） | 没有探活数据时全部落在这里 → 行为与旧版一致 |
| `http-403` | 403/401（网络锁，以移动魔百和 `cmvideo` 为主） | 低 | 非对应运营商网络基本打不开 |
| `ipv6-no-route` | IPv6 字面量且本机无 IPv6 出口 | 低 | 仅 IPv6 用户可用 |
| `conn-fail` / `ssl-fail` | 连接失败 / 证书或 TLS 失败 | 低 | |
| `dns-fail` / `http-404` | 域名不存在 / 404 | 最低 | 死链，不应占据主列表 |
| `rtp` | `rtp://` 组播 | 低（沿用旧规则） | 不参与探活 |

选优排序维度（`scripts/lib/select.py`）：

```
(rtp 降权, 时效签名降权, URL 健康度, 区域, 频道 priority, 源 priority, 是否命中标准表, 名称长度)
```

**无 `output/health.json` 时，健康度维度全体取 `unknown`，排序与旧版逐位一致**——这条有单测覆盖
（`tests/test_select_health.py`），可随时回退。

## 3. 怎么跑

```bash
# 1) 探活：默认探 output/live.m3u + output/live_backup.m3u
python scripts/probe.py --egress-label wuhan-unicom

# 2) 重新选优（读 output/health.json，生成 health 感知的列表）
python scripts/collect.py
python scripts/verify_outputs.py

# 可选：把扩展列表也纳入探活（数据量大，按需）
python scripts/probe.py --include-more --limit 2000
```

参数见 `config/probe.yaml`（并发、超时、首片字节、是否下探分片、有效期、分列开关）。

## 4. 出口网络（必须先说清楚）

**探活结果只代表「探测出口网络」的可达性。**

| 出口 | 适合的结论 | 不适合的结论 |
|------|-----------|--------------|
| 家里（如武汉联通 AS4837） | 我这条线能不能看 | 全国都能看 |
| GitHub Actions（美国） | 海外能不能直达 | 大陆能不能看 |
| 自托管 runner（`self-hosted,iptv`） | 该出口的视角 | 全国可用 |

因此：

- **不要**把云端 CI 的探活结果写进 README 当结论；
- 主列表的「可播优先」排序，价值最大的是**你自己的网络**跑出来的 `health.json`；
- `output/health.json` 里记录 `egress.label`，谁看谁心里有数。

## 5. 分列文件（本机产物）

| 文件 | 内容 | 用途 |
|------|------|------|
| `live_ipv6.m3u` | 仅 IPv6 可播（本机无 v6 出口时的降级项） | 有 IPv6 的设备单独订 |
| `live_cmcc.m3u` | 403 网络锁（以移动魔百和为主） | 移动宽带用户单独订 |
| `live_signed.m3u` | 带时效签名参数（会过期） | 临时应急用，别当长期订阅 |

这三个分列是**本机探活的副产物**，内容取决于出口网络，默认不进仓库（见 `.gitignore`）。
`output/health.json` 不同：它体积小、是选优的依据，**可以**提交进仓库让云端日更在有效期内沿用。

## 6. 有效期与回退

- `config/probe.yaml` 的 `max_age_days`（默认 7）内的健康数据才参与选优；
- 单条 URL 超过有效期 → 该条降级为 `unknown`（不奖惩）；
- 整体数据过期 → `collect.py` 打印告警并按旧口径输出，不会因为「探活挂了」把列表搞坏；
- `collect.py` 可通过 `settings.use_url_health: false` 一键关闭健康度加权。

## 7. 与 CI 的关系

云端 `collect.yml` 默认**没有**探活步骤：

- 仓库里没有 `output/health.json`（或已过期）→ CI 的日更按旧口径出列表，行为与历史一致；
- 如果需要「本地探活结果也参与日更选优」，两种做法（任选其一，不要混用）：
  1. **本地日更**：家里机器定时 `probe.py` → `collect.py` → 提交（结果最贴近你的网络）；
  2. **提交健康数据**：把本机 `health.json` 提交进仓库，CI 在有效期内沿用（注意它会带来 diff 噪音）。

## 8. 每周手动一次的最短流程（推荐起步方式）

在**家里网络**的机器上（Windows / macOS / Linux 均可）：

```bash
# 只需第一次：准备环境
git clone https://github.com/Hawaiine/Oasisic-IPTV.git && cd Oasisic-IPTV
python3 -m venv .venv
# Windows: .venv\Scripts\pip install -r requirements.txt
.venv/bin/pip install -r requirements.txt

# 每周一次：拉最新 → 探活 → 重排 → 校验
git pull
.venv/bin/python scripts/probe.py --egress-label wuhan-unicom    # 输出 output/health.json
.venv/bin/python scripts/collect.py                              # 读健康度重排主列表
.venv/bin/python scripts/verify_outputs.py                       # 必须全绿
```

然后把 `output/health.json` 交给维护者提交（或自行 commit/push）。
云端日更在 **7 天**内会沿用这份探活结果，过期自动回退旧口径——**不跑也不会坏**，只是排序退回旧规则。