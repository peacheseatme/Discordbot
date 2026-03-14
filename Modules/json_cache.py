"""
In-memory JSON cache for hot-path config/data files.
Reduces disk I/O on every message, level card, etc.
"""

from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any

_CACHE: dict[str, Any] = {}


def _path_key(path: str | Path) -> str:
    return str(Path(path).resolve())


def _copy_if_mutable(obj: Any) -> Any:
    """Return a deep copy for mutable types so callers cannot corrupt the cache."""
    if isinstance(obj, (dict, list)):
        return copy.deepcopy(obj)
    return obj


def get(path: str | Path, default: Any = None) -> Any:
    """Load JSON from cache or disk. Returns cached copy on hit."""
    key = _path_key(path)
    if key in _CACHE:
        return _CACHE[key]
    p = Path(path)
    if not p.exists():
        base = default if default is not None else {}
        return _copy_if_mutable(base)
    try:
        with p.open("r", encoding="utf-8") as fp:
            data = json.load(fp)
        _CACHE[key] = data
        return data
    except (OSError, json.JSONDecodeError):
        base = default if default is not None else {}
        return _copy_if_mutable(base)


def set_(path: str | Path, data: Any) -> None:
    """Write JSON to disk and update cache."""
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("w", encoding="utf-8") as fp:
        json.dump(data, fp, indent=2, ensure_ascii=True)
    _CACHE[_path_key(path)] = data


def invalidate(path: str | Path) -> None:
    """Remove path from cache (e.g. after external write)."""
    _CACHE.pop(_path_key(path), None)
