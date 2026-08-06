"""调用上游 ProTAS 训练/预测。"""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path
from typing import Any

from src.data.paths import mstcn_dataset_dir, protas_root


def _require_protas(cfg: dict[str, Any]) -> Path:
    root = protas_root(cfg)
    main_py = root / "main.py"
    if not main_py.exists():
        raise FileNotFoundError(
            f"ProTAS not found at {root}. Run: python scripts/clone_third_party.py"
        )
    return root


def build_protas_command(cfg: dict[str, Any], action: str) -> list[str]:
    train = cfg.get("train", {})
    cmd = [
        sys.executable,
        "main.py",
        "--action",
        action,
        "--dataset",
        str(train.get("dataset", "gtea")),
        "--split",
        str(train.get("split", "1")),
        "--exp_id",
        str(train.get("exp_id", "run0")),
    ]
    if train.get("causal", True):
        cmd.append("--causal")
    if train.get("use_graph", True):
        cmd.append("--graph")
    if train.get("learnable_graph", True):
        cmd.append("--learnable_graph")
    # 常见可选超参（上游若未定义会被忽略或报错——用环境变量更稳时再扩）
    return cmd


def run_protas(cfg: dict[str, Any], action: str = "train") -> int:
    root = _require_protas(cfg)
    dataset = str(cfg.get("train", {}).get("dataset", "gtea"))
    data_dir = mstcn_dataset_dir(cfg, dataset)
    if not data_dir.exists():
        raise FileNotFoundError(
            f"dataset dir missing: {data_dir}. "
            "Download T1 (Zenodo) and extract, or link features into this path."
        )

    env = os.environ.copy()
    gpu_ids = cfg.get("hardware", {}).get("gpu_ids", [0])
    if cfg.get("hardware", {}).get("device") == "cuda" and gpu_ids:
        env["CUDA_VISIBLE_DEVICES"] = ",".join(str(i) for i in gpu_ids)

    cmd = build_protas_command(cfg, action)
    print("+", " ".join(cmd), f"(cwd={root})")
    print(f"expected_data_dir={data_dir}")
    return subprocess.call(cmd, cwd=str(root), env=env)
