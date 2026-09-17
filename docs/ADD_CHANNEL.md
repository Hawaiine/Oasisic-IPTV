# 向标准频道表加台

主列表 `live.m3u` **只收标准表命中**。想让某台出现在精选列表，改表，不要往主列表泄洪。
完整的字段规范、收录判据与命名规范见 [CHANNEL_STANDARD.md](CHANNEL_STANDARD.md)。

## 推荐流程（批量扩容）

```bash
python scripts/suggest_channels.py          # ① 从 live_more 长尾里挑「能匹配上游 EPG」的候选
python scripts/suggest_channels.py --apply  # ② 复核后入库（幂等）
python scripts/fetch_missing_logos.py       # ③ 补台标（只认本仓库 logo/，抓不到就留空）
python scripts/sync_epg_ids.py              # ④ 对齐 epg_id（缺失进 data/epg_missing.txt）
python scripts/collect.py && python scripts/fetch_epg.py && python scripts/verify_outputs.py
```

## channels.json（手工加台）

```json
{
  "standard_name": "河北卫视",
  "display_name": "河北卫视",
  "category": "weishi",
  "tvg_id": "HEBTV",
  "epg_id": "河北卫视",
  "tvg_logo": "https://cdn.jsdelivr.net/gh/Hawaiine/Oasisic-IPTV@main/logo/HEBTV.png"
}
```

规则：

- `standard_name` / `display_name` 必须符合命名规范（央视带节目名，卫视无「高清/HD」）。
- `category` 只能是：cctv / weishi / local / gangtai / sports / live / overseas / hotel / radio / other。
- `tvg_id`：台标文件名（`logo/<tvg_id>.png` 必须真实存在，否则输出时会置空防 404）。
- `epg_id`：输出到 `#EXTINF` 的 `tvg-id`，**必须**能在 `epg_sources` 里找到且有 programme；查不到写 `null`
  （跑 `python scripts/sync_epg_ids.py` 会自动判定并生成缺口清单，别凭印象填）。
- `tvg_logo` **只允许**本仓库 `logo/` 的 jsDelivr 地址或留空；禁止第三方 URL。
- 可选字段：
  - `priority`：整数，越小越优先（默认 50）。央视核心台可写 10~20，让其在同区域同源竞争时胜出。
  - `preferred_region`：`cn` / `hk_tw` 等。命中该区域的源会被提到 cn 同级再按 priority 竞争；港澳台频道建议 `hk_tw`。

## aliases.json

key **必须**是已有 `standard_name`（zero-orphan）：

```json
{
  "河北卫视": ["河北", "Hebei TV", "河北卫视频道"]
}
```

别名同时服务于两件事：源名称匹配（清洗后的名字 → 标准台）和 EPG 名称匹配（上游中文名 → epg_id）。
上游名字不一样时（如 `陕西农林卫视` ↔ 我们的 `农林卫视`），把上游名写进别名即可自动对齐。

## 校验

```bash
python scripts/verify_outputs.py   # 含 zero-orphan、EPG 覆盖率硬检查
pytest tests/ -q
```