# 常见问题

## live_more 与精选的关系

精选是 **`live.m3u`**，只收标准表频道且一台一链。
扩展列表是 **`live_more.m3u`**，收录未入表但能采到的频道，按关键词分类，但只有频道名和链接，不承诺 EPG / 台标完整。

## 某个台看不了

1. 看 `data/epg_missing.txt`：没节目单的频道在 EPG 客户端里会白屏，不影响播放。
2. 看 `data/logo_missing.txt`：缺台标只影响观感，不影响播放。
3. 看 `docs/PLAYABILITY.md`：用 `scripts/probe.py` 在本机测本出口可达性。
4. 源失败或失效：在 `config/sources.yaml` 里 disable 对应源；不要手工删 M3U 条目。

## 日更里的 guide.xml 为什么变小 / 被裁剪

`guide.xml` 已从 git 历史中移除，只保留在 CI Artifacts（30 天）。本地仍可生成裁剪版，见 `docs/EPG.md`。

## 贡献代码

见 [docs/CONTRIBUTING.md](docs/CONTRIBUTING.md)。

## 合规

本仓库仅聚合公开链接，不托管媒体内容。使用者自行承担合规责任。地域源、酒店源、IPV6 源、`rtp://` 组播可以收录，但能否播放取决于本地网络与版权环境。
