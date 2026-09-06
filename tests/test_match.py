from lib.match import ChannelMatcher, attach_match


CHANNELS = [
    {
        "standard_name": "CCTV-1 综合",
        "display_name": "CCTV-1 综合",
        "category": "cctv",
        "tvg_id": "CCTV1",
    },
    {
        "standard_name": "湖南卫视",
        "display_name": "湖南卫视",
        "category": "weishi",
        "tvg_id": "HunanTV",
    },
    {
        "standard_name": "东方卫视",
        "display_name": "东方卫视",
        "category": "weishi",
        "tvg_id": "DragonTV",
    },
]
ALIASES = {
    "CCTV-1 综合": ["CCTV1", "央视一套"],
    "湖南卫视": ["芒果台"],
    "东方卫视": ["上海东方卫视"],
}


def test_exact_and_alias() -> None:
    m = ChannelMatcher(CHANNELS, ALIASES)
    assert m.match("CCTV-1 综合")["standard_name"] == "CCTV-1 综合"
    assert m.match("CCTV1")["standard_name"] == "CCTV-1 综合"
    assert m.match("芒果台")["standard_name"] == "湖南卫视"
    assert m.match("上海东方卫视")["standard_name"] == "东方卫视"


def test_unknown_returns_none() -> None:
    m = ChannelMatcher(CHANNELS, ALIASES)
    assert m.match("XX地方台") is None


def test_attach_match_flags() -> None:
    m = ChannelMatcher(CHANNELS, ALIASES)
    out = attach_match([{"name": "湖南卫视高清", "url": "u1"}, {"name": "未知台", "url": "u2"}], m)
    assert out[0]["matched"] is True
    assert out[0]["display_name"] == "湖南卫视"
    assert out[1]["matched"] is False
