# 客户端兼容性矩阵

本矩阵基于项目实测与社区反馈，覆盖常见播放器/机顶盒。**兼容性会随固件版本变化**，以最新实测为准。

| 客户端 | 主列表 | 备份列表 | EPG | 台标 | 备注 |
|--------|--------|----------|-----|------|------|
| TiviMate (Android TV) | ✅ | ✅ | ✅ 自动读 url-tvg | ✅ | 支持多源故障转移；备份列表可显著改善卡顿/失效时的体验 |
| APTV (Apple TV / iOS / macOS) | ✅ | ✅ | ✅ 手动填地址 | ✅ | 订阅设置里开「自动更新 EPG」；iOS 限制后台刷新 |
| TVBox / 影视仓 / 易播 | ✅ | 视壳子 | ⚠️ 部分支持 | ⚠️ 部分支持 | 不同壳子/接口能力差异大；先试 url-tvg 自动读取，不行再手动填 EPG 地址 |
| Kodi + PVR IPTV Simple Client | ✅ | ❌ 一般不订 | ✅ 手动填 | ✅ | 专业但配置多；建议关闭「允许图形旋转」减少台标闪烁 |
| VLC (Win/Mac/Android) | ✅ | ❌ | ⚠️ 弱 | ✅ | 当直播源用；EPG 支持有限 |
| PotPlayer (Windows) | ✅ | ❌ | ⚠️ 需插件 | ✅ | 当直播源用；EPG 需额外插件 |
| IPTV Smarters / XTREAM | ✅ | ❌ | ✅ | ✅ | 需手动导入 M3U |
| 小米盒子 / 华为盒子 | ✅ | ❌ | ⚠️ | ⚠️ | 系统播放器能力有限；建议装 TiviMate 或 TVBox |
| 创维 / 海信 / 康佳等国产 | ✅ | ❌ | ⚠️ | ⚠️ | 各品牌差异大；以自带播放器实测为准 |
| Plex / Emby / Jellyfin | ✅ | ❌ | ❌ | ✅ | 需第三方插件或手动导入 |

## 推荐订阅策略

| 用户类型 | 推荐订阅 |
|----------|----------|
| 普通用户 | 只订 `live.m3u` |
| 网络不稳定 / 多线路 | `live.m3u` + `live_backup.m3u` |
| 追求完整节目单 | `live.m3u` + EPG 地址 `https://live.fanmingming.com/e.xml` |
| 分类观看 | `live.m3u` + 对应分类文件（`live_cctv.m3u` 等） |

## 故障排查

1. **某个台看不了**：看 `data/epg_missing.txt`（无节目单）和 `data/logo_missing.txt`（缺台标）；用 `scripts/probe.py` 在本机测可达性
2. **EPG 不显示**：确认播放器支持 XMLTV；手动填 `https://live.fanmingming.com/e.xml`；等待客户端自动更新
3. **台标不显示**：确认网络能访问 `cdn.jsdelivr.net`；部分客户端需手动刷新台标缓存
4. **卡顿/缓冲**：换用 `live_backup.m3u` 的多源故障转移；检查本地网络到源站可达性
