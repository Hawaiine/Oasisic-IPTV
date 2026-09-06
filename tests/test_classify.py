from lib.classify import classify_entries, classify_name


def test_keyword_fallback() -> None:
    assert classify_name("CCTV-1 综合") == "cctv"
    assert classify_name("湖南卫视") == "weishi"
    assert classify_name("凤凰卫视中文台") == "gangtai"
    assert classify_name("斗鱼某某") == "live"
    assert classify_name("中央人民广播电台") == "radio"


def test_matched_keeps_table_category() -> None:
    out = classify_entries(
        [
            {
                "matched": True,
                "category": "weishi",
                "cleaned_name": "湖南卫视",
                "name": "湖南卫视",
            }
        ]
    )
    assert out[0]["category"] == "weishi"
    assert out[0]["group_title"] == "卫视"
