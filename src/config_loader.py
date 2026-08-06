"""加载根目录 config.json。"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG = ROOT / "config.json"


def load_config(path: Path | None = None) -> dict[str, Any]:
    cfg_path = path or DEFAULT_CONFIG
    if not cfg_path.exists():
        raise FileNotFoundError(f"missing config: {cfg_path}")
    return json.loads(cfg_path.read_text(encoding="utf-8"))


def project_root() -> Path:
    return ROOT


def resolve_path(cfg: dict[str, Any], key: str) -> Path:
    rel = cfg.get("paths", {}).get(key, key)
    p = Path(rel)
    return p if p.is_absolute() else ROOT / p
