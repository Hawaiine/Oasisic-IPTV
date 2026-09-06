# 向标准频道表加台

主列表 `live.m3u` **只收标准表命中**。想让某台出现在精选列表，改表，不要往主列表泄洪。

## channels.json

```json
{
  "standard_name": "河北卫视",
  "display_name": "河北卫视",
  "category": "weishi",
  "tvg_id": "HEBTV",
  "tvg_logo": "https://live.fanmingming.com/tv/HEBTV.png"
}
```

规则：

- `standard_name` 与 `display_name` 必须符合命名规范（央视带节目名，卫视无「高清/HD」）。
- `category` 只能是：cctv / weishi / local / gangtai / sports / live / overseas / hotel / radio / other。
- `tvg_id` 尽量与 fanmingming 台标文件名一致。

## aliases.json

key **必须**是已有 `standard_name`（zero-orphan）：

```json
{
  "河北卫视": ["河北", "Hebei TV", "河北卫视频道"]
}
```

校验：

```bash
python - <<'PY'
import json
from pathlib import Path
ch = json.loads(Path("data/channels.json").read_text())
al = json.loads(Path("data/aliases.json").read_text())
std = {c["standard_name"] for c in ch}
orph = [k for k in al if k not in std]
assert not orph, orph
print("ok", len(ch), "channels")
PY
pytest tests/ -q
```
