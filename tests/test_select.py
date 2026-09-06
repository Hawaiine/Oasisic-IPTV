from lib.select import order_for_output, select_best, split_catalog_more


def _e(**kw):
    base = {
        "name": "x",
        "url": "http://a",
        "matched": True,
        "standard_name": "湖南卫视",
        "display_name": "湖南卫视",
        "category": "weishi",
        "source_region": "cn",
        "source_priority": 50,
    }
    base.update(kw)
    return base


def test_max_keep_one() -> None:
    items = [
        _e(url="http://a/1", source_priority=10),
        _e(url="http://a/2", source_priority=90),
    ]
    out = select_best(items, max_keep=1)
    video = [x for x in out if x["category"] != "radio"]
    assert len(video) == 1
    assert video[0]["url"] == "http://a/1"


def test_channel_priority_wins_over_source_priority() -> None:
    """频道级 priority 应优先于源 priority（同区域、同 rtp 时）。"""
    items = [
        _e(url="http://srcA", source_priority=90, channel_priority=10),
        _e(url="http://srcB", source_priority=10, channel_priority=50),
    ]
    out = select_best(items, max_keep=1)
    video = [x for x in out if x["category"] != "radio"]
    assert video[0]["url"] == "http://srcA"


def test_preferred_region_boosts_match() -> None:
    """preferred_region 命中：hk_tw 源与 cn 源同级竞争，再按源 priority。"""
    items = [
        _e(
            url="http://hk",
            standard_name="凤凰卫视中文台",
            display_name="凤凰卫视中文台",
            source_region="hk_tw",
            source_priority=10,
            preferred_region="hk_tw",
        ),
        _e(
            url="http://cn",
            standard_name="凤凰卫视中文台",
            display_name="凤凰卫视中文台",
            source_region="cn",
            source_priority=90,
            preferred_region="hk_tw",
        ),
    ]
    out = select_best(items, max_keep=1)
    video = [x for x in out if x["category"] != "radio"]
    assert video[0]["url"] == "http://hk"


def test_no_preferred_region_keeps_old_order() -> None:
    """无 preferred_region / channel_priority 时行为与旧版一致（cn 先于 hk_tw）。"""
    items = [
        _e(url="http://hk", source_region="hk_tw", source_priority=1),
        _e(url="http://cn", source_region="cn", source_priority=90),
    ]
    out = select_best(items, max_keep=1)
    video = [x for x in out if x["category"] != "radio"]
    assert video[0]["url"] == "http://cn"


def test_global_url_dedup_non_radio_wins() -> None:
    items = [
        _e(url="http://same", category="radio", matched=False, standard_name="电台"),
        _e(url="http://same", category="weishi", matched=True, standard_name="湖南卫视"),
    ]
    out = select_best(items, max_keep=1)
    assert len(out) == 1
    assert out[0]["category"] == "weishi"


def test_rtp_penalty() -> None:
    items = [
        _e(url="rtp://1.2.3.4:1234", source_priority=1),
        _e(url="http://better", source_priority=90),
    ]
    out = select_best(items, max_keep=1)
    assert out[0]["url"].startswith("http")


def test_cctv_numeric_order() -> None:
    items = [
        _e(display_name="CCTV-10 科教", standard_name="CCTV-10 科教", category="cctv", url="http://c10"),
        _e(display_name="CCTV-1 综合", standard_name="CCTV-1 综合", category="cctv", url="http://c1"),
        _e(display_name="CCTV-5+ 体育赛事", standard_name="CCTV-5+ 体育赛事", category="cctv", url="http://c5p"),
        _e(display_name="CCTV-5 体育", standard_name="CCTV-5 体育", category="cctv", url="http://c5"),
    ]
    names = [x["display_name"] for x in order_for_output(items)]
    assert names == ["CCTV-1 综合", "CCTV-5 体育", "CCTV-5+ 体育赛事", "CCTV-10 科教"]


def test_backup_keep_three_distinct_urls() -> None:
    items = [
        _e(url="http://a/1", source_priority=10),
        _e(url="http://a/2", source_priority=20),
        _e(url="http://a/3", source_priority=30),
        _e(url="http://a/4", source_priority=40),
    ]
    out = select_best(items, max_keep=3)
    urls = [x["url"] for x in out if x["category"] != "radio"]
    assert urls == ["http://a/1", "http://a/2", "http://a/3"]


def test_split_catalog_more() -> None:
    items = [
        _e(matched=True, standard_name="湖南卫视"),
        _e(matched=False, standard_name="XX地方台", display_name="XX地方台", category="local", url="http://z"),
        _e(matched=False, category="radio", standard_name="中央台", url="http://r", name="中央台"),
        _e(matched=True, category="overseas", standard_name="NHK", url="http://n"),
    ]
    catalog, more, radio = split_catalog_more(items, main_include_overseas=False)
    assert [c["standard_name"] for c in catalog] == ["湖南卫视"]
    assert any(x["standard_name"] == "XX地方台" for x in more)
    assert any(x["standard_name"] == "NHK" for x in more)
    assert len(radio) == 1

