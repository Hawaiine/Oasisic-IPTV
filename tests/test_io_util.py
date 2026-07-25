# coding: utf-8
"""Tests for lib/io_util.py."""

import json
import os
import tempfile

from lib.io_util import data_path, load_json, save_json, project_root


class TestProjectRoot:
    def test_is_absolute_path(self):
        root = project_root()
        assert os.path.isabs(root)

    def test_project_root_is_dir(self):
        assert os.path.isdir(project_root())

    def test_has_config_settings(self):
        path = os.path.join(project_root(), "config", "settings.yaml")
        assert os.path.isfile(path)

    def test_has_config_sources(self):
        path = os.path.join(project_root(), "config", "sources.yaml")
        assert os.path.isfile(path)

    def test_data_path_channels_exists(self):
        path = data_path("channels.json")
        assert os.path.isfile(path)

    def test_data_path_is_absolute(self):
        path = data_path("channels.json")
        assert os.path.isabs(path)

    def test_data_path_ends_data(self):
        path = data_path("channels.json")
        # Should contain "data" in the path
        assert "data" in path.split(os.sep)


class TestLoadSaveJson:
    def test_save_and_load_roundtrip(self):
        data = {"key": "value", "num": 42}
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            tmp_path = f.name
        try:
            save_json(tmp_path, data)
            loaded = load_json(tmp_path)
            assert loaded == data
        finally:
            os.unlink(tmp_path)

    def test_save_creates_missing_dirs(self):
        base = tempfile.mkdtemp()
        nested = os.path.join(base, "a", "b", "test.json")
        try:
            save_json(nested, {"ok": True})
            assert os.path.isfile(nested)
            loaded = load_json(nested)
            assert loaded["ok"] is True
        finally:
            import shutil
            shutil.rmtree(base)