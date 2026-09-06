from lib.io_util import project_root


def test_project_root_is_repo() -> None:
    root = project_root()
    assert (root / "config" / "sources.yaml").exists()
    assert (root / "scripts" / "collect.py").exists()
    # 不得把克隆目录名写死
    assert root.name  # 任意目录名均可
