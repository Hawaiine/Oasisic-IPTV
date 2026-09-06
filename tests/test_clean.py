from lib.clean import (
    _CCTV_PROGRAM,
    _WEISHI_FIX,
    clean_channel_name,
)


def test_cctv1_with_program() -> None:
    assert clean_channel_name("CCTV1") == "CCTV-1 综合"
    assert clean_channel_name("CCTV1综合") == "CCTV-1 综合"
    assert clean_channel_name("CCTV-1高清") == "CCTV-1 综合"
    assert clean_channel_name("CCTV1HD") == "CCTV-1 综合"
    assert "  " not in clean_channel_name("CCTV1综合")


def test_cctv5_plus() -> None:
    assert clean_channel_name("CCTV5+") == "CCTV-5+ 体育赛事"
    assert clean_channel_name("CCTV-5+") == "CCTV-5+ 体育赛事"


def test_cctv4k_kept() -> None:
    assert clean_channel_name("CCTV-4K") == "CCTV-4K 超高清"
    assert clean_channel_name("CCTV4K超高清") == "CCTV-4K 超高清"


def test_weishi_aliases() -> None:
    assert clean_channel_name("上海东方卫视") == "东方卫视"
    assert clean_channel_name("福建东南卫视") == "东南卫视"
    assert clean_channel_name("湖南卫视高清") == "湖南卫视"
    assert clean_channel_name("浙江卫视频道") == "浙江卫视"


def test_strip_tags() -> None:
    assert "高清" not in clean_channel_name("江苏卫视高清")
    assert "IPV6" not in clean_channel_name("北京卫视 IPV6").upper()
    assert "备用" not in clean_channel_name("广东卫视备用")
    assert "50 FPS" not in clean_channel_name("湖南卫视 50 FPS")
    assert "60fps" not in clean_channel_name("东方卫视 60fps").lower()


def test_external_data_loaded() -> None:
    """data/cctv_programs.json 与 weishi_aliases.json 应被加载且完整。"""
    assert _CCTV_PROGRAM["7"] == "国防军事"
    assert _CCTV_PROGRAM["13"] == "新闻"
    assert _WEISHI_FIX["上海东方卫视"] == "东方卫视"
    assert _WEISHI_FIX["旅游卫视"] == "海南卫视"
