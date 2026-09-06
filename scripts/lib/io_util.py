"""文件读写与路径工具。"""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from typing import Any

import yaml


def project_root() -> Path:
    """仓库根目录（scripts/lib 的上两级）。不依赖目录名，避免克隆路径断言。"""
    return Path(__file__).resolve().parent.parent.parent


def load_yaml(path: str | Path) -> Any:
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def load_json(path: str | Path) -> Any:
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def save_json(path: str | Path, data: Any, *, indent: int = 2) -> None:
    text = json.dumps(data, ensure_ascii=False, indent=indent) + "\n"
    save_text(path, text)


def save_text(path: str | Path, text: str) -> None:
    """原子写入，避免半成品文件。"""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=path.name + ".", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as f:
            f.write(text)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, path)
    except Exception:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise
