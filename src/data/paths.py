"""数据路径与目录约定。"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from src.config_loader import project_root, resolve_path


def ensure_data_dirs(cfg: dict[str, Any]) -> dict[str, Path]:
    mapping = {}
    for key in ("public_data", "features", "internal_data", "outputs", "third_party"):
        path = resolve_path(cfg, key)
        path.mkdir(parents=True, exist_ok=True)
        mapping[key] = path
    return mapping


def mstcn_dataset_dir(cfg: dict[str, Any], dataset: str) -> Path:
    """Zenodo MS-TCN 解压后常见布局: data/<dataset>/{features,groundTruth,splits,mapping.txt}"""
    base = resolve_path(cfg, "features") / "mstcn_zenodo"
    # 兼容 zip 解压出 data/ 或直接 gtea/
    candidates = [
        base / "data" / dataset,
        base / dataset,
        project_root() / "data" / "features" / "mstcn_zenodo" / "data" / dataset,
        project_root() / "third_party" / "ProTAS" / "data" / dataset,
    ]
    for c in candidates:
        if c.exists():
            return c
    return candidates[0]


def protas_root(cfg: dict[str, Any]) -> Path:
    meta = cfg.get("third_party", {}).get("ProTAS", {})
    return project_root() / meta.get("path", "third_party/ProTAS")


def egoper_root(cfg: dict[str, Any]) -> Path:
    meta = cfg.get("third_party", {}).get("EgoPER_official", {})
    return project_root() / meta.get("path", "third_party/EgoPER")
