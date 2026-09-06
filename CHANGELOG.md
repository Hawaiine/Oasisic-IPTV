## 采集报告 2026-09-06 10:43:52

- 状态: catalog=115 / more=3000 / radio=59
- 源成功率: 12/12 (100%)
- 时区: Asia/Shanghai

| 分类 | 条数 |
|------|------|
| 卫视 | 34 |
| 各省市 | 29 |
| 央视 | 26 |
| 港澳台 | 19 |
| 体育 | 6 |
| 网络直播 | 1 |

---

# CHANGELOG

## 工程日志

**EPG** | 2026-09-06 | 主列表写入 url-tvg（fanmingming e.xml）；裁剪版 guide.xml 进 git；programme 按 (channel,start,stop) 去重；删除 epg_commit；EPG 失败 Discord 告警、CI 不红；README 补充播放器用法。

**从零重构** | 2026-09-06 | 目录制双列表（live.m3u 一台一链 + live_more.m3u）；标准表覆盖全部央视/省级卫视/主要地方台/港澳台；源生命周期（list/validate/stats/enable/disable + 连续失败自动禁用）；无测活；GitHub Actions 日更（中文 emoji commit）。

---

采集报告将由 `scripts/generate_report.py --write-changelog` 写在本文件顶部。
