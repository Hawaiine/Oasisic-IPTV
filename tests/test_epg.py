from xml.etree.ElementTree import tostring

from fetch_epg import merge_and_clip


XML_A = """<?xml version="1.0"?>
<tv>
  <channel id="CCTV1"><display-name>CCTV-1</display-name></channel>
  <channel id="HunanTV"><display-name>湖南卫视</display-name></channel>
  <channel id="UNKNOWN"><display-name>未知</display-name></channel>
  <programme channel="CCTV1" start="20260101000000 +0800" stop="20260101010000 +0800">
    <title>新闻</title>
  </programme>
  <programme channel="HunanTV" start="20260101000000 +0800" stop="20260101020000 +0800">
    <title>综艺A</title>
  </programme>
  <programme channel="UNKNOWN" start="20260101000000 +0800" stop="20260101010000 +0800">
    <title>应被裁掉</title>
  </programme>
</tv>
"""

XML_B = """<?xml version="1.0"?>
<tv>
  <channel id="CCTV1"><display-name>CCTV-1-dup</display-name></channel>
  <programme channel="CCTV1" start="20260101000000 +0800" stop="20260101010000 +0800">
    <title>重复应丢</title>
  </programme>
  <programme channel="CCTV1" start="20260101010000 +0800" stop="20260101020000 +0800">
    <title>晚间</title>
  </programme>
</tv>
"""


def test_clip_and_dedup() -> None:
    root, stats = merge_and_clip([XML_A, XML_B], {"CCTV1", "HunanTV"})
    ids = [c.get("id") for c in root.findall("channel")]
    assert ids == ["CCTV1", "HunanTV"]
    titles = [p.findtext("title") for p in root.findall("programme")]
    assert titles == ["新闻", "综艺A", "晚间"]
    assert stats["programme_dup"] == 1
    assert stats["channel_skipped"] >= 1
    assert "应被裁掉" not in tostring(root, encoding="unicode")
    assert "重复应丢" not in tostring(root, encoding="unicode")
