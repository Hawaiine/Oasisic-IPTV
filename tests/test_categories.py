from lib.categories import RADIO_KEY, group_title, iter_main_order


def test_chinese_group_titles() -> None:
    assert group_title("cctv") == "央视"
    assert group_title("weishi") == "卫视"
    assert group_title("local") == "各省市"
    assert group_title("unknown") == "其他"


def test_main_order_excludes_radio() -> None:
    order = list(iter_main_order())
    assert order[0] == "cctv"
    assert RADIO_KEY not in order
    assert "other" in order
