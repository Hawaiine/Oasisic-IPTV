## 采集报告 2026-09-06 11:22:41

- 状态: catalog=115 / more=1674 / backup=321 / radio=3
- 源成功率: 14/14 (100%)
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

**源治理** | 2026-09-06 | 剔除 ssili-tv / Free-TV / iptv-org jp·kr；新增 fanmingming-itv、hujingguang、YanG Gather、zilong-best、TianmuTNT；主+备列表（live_backup 每台最多 3 URL）；酒店源降权保留；GitHub 描述去掉测活。

**从零重构** | 2026-09-06 | 目录制双列表（live.m3u 一台一链 + live_more.m3u）；标准表覆盖全部央视/省级卫视/主要地方台/港澳台；源生命周期（list/validate/stats/enable/disable + 连续失败自动禁用）；无测活；GitHub Actions 日更（中文 emoji commit）。

---

采集报告将由 `scripts/generate_report.py --write-changelog` 写在本文件顶部。
