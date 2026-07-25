# coding: utf-8
"""
I/O utilities for the Oasisic-IPTV project.

Provides helpers for loading/saving JSON/YAML and resolving the
project root directory.
"""

from __future__ import annotations

import json
import os
import typing as t

import yaml

# ── Project root ───────────────────────────────────────────────────

_PROJECT_ROOT: str | None = None


def project_root() -> str:
    """Return the absolute path to the project root directory."""
    global _PROJECT_ROOT
    if _PROJECT_ROOT is None:
        _PROJECT_ROOT = os.path.abspath(
            os.path.join(os.path.dirname(__file__), "..", "..")
        )
    return _PROJECT_ROOT


def data_path(*parts: str) -> str:
    """Return an absolute path under ``data/``."""
    return os.path.join(project_root(), "data", *parts)


def config_path(*parts: str) -> str:
    """Return an absolute path under ``config/``."""
    return os.path.join(project_root(), "config", *parts)


# ── JSON ───────────────────────────────────────────────────────────


def load_json(path: str) -> t.Any:
    """
    Load a JSON file and return the deserialised data.

    Parameters
    ----------
    path : str
        Absolute or relative path to the JSON file.

    Returns
    -------
    Any
        Deserialised JSON data.
    """
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_json(path: str, data: t.Any, indent: int = 2, **kwargs: t.Any) -> None:
    """
    Serialise ``data`` to JSON and write to ``path``.

    Parameters
    ----------
    path : str
        Output file path.
    data : Any
        Data to serialise.
    indent : int
        JSON indent (default 2).
    """
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=indent, **kwargs)


# ── YAML ───────────────────────────────────────────────────────────


def load_yaml(path: str) -> t.Any:
    """
    Load a YAML file and return the deserialised data.

    Parameters
    ----------
    path : str
        Path to the YAML file.

    Returns
    -------
    Any
        Deserialised YAML data.
    """
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)