from collect import should_suggest_disable


def test_non_core_three_failures_suggest_manual_review():
    assert should_suggest_disable({"consecutive_fail": 3}, {"core": False, "enabled": True}, 3)


def test_core_sources_never_get_disable_suggestion():
    assert not should_suggest_disable({"consecutive_fail": 9}, {"core": True, "enabled": True}, 3)


def test_disabled_source_does_not_get_disable_suggestion():
    assert not should_suggest_disable({"consecutive_fail": 9}, {"core": False, "enabled": False}, 3)


def test_below_threshold_does_not_get_disable_suggestion():
    assert not should_suggest_disable({"consecutive_fail": 2}, {"core": False, "enabled": True}, 3)


def test_record_source_stats_suggests_without_mutating_sources_yaml(tmp_path, monkeypatch):
    import json
    import collect

    (tmp_path / "data").mkdir()
    (tmp_path / "config").mkdir()
    sources_path = tmp_path / "config" / "sources.yaml"
    source_text = "sources:\n  - key: unstable\n    enabled: true\n    core: false\n"
    sources_path.write_text(source_text, encoding="utf-8")
    stats_path = tmp_path / "data" / "source_stats.json"
    stats_path.write_text(json.dumps({"schema_version": 1, "sources": {
        "unstable": {"ok": 0, "fail": 2, "consecutive_fail": 2, "last_ok": "", "last_fail": "", "last_count": 0}
    }}), encoding="utf-8")
    monkeypatch.setattr(collect, "project_root", lambda: tmp_path)

    collect.record_source_stats([{
        "key": "unstable",
        "source": {"key": "unstable", "enabled": True, "core": False},
        "ok": False,
        "error": "HTTP 503",
    }], {"auto_disable_fail_days": 3})

    assert sources_path.read_text(encoding="utf-8") == source_text
    saved = json.loads(stats_path.read_text(encoding="utf-8"))
    assert saved["sources"]["unstable"]["suggest_disable"] is True
    assert saved["sources"]["unstable"]["consecutive_fail"] == 3
