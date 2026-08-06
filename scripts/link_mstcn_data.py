#!/usr/bin/env python3
"""将 Zenodo 解压后的 MS-TCN 数据链接/拷贝到 ProTAS/data 下。"""
from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.config_loader import load_config
from src.data.paths import mstcn_dataset_dir, protas_root


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", default=None)
    parser.add_argument("--copy", action="store_true", help="拷贝而非 symlink")
    args = parser.parse_args()
    cfg = load_config()
    dataset = args.dataset or str(cfg.get("train", {}).get("dataset", "gtea"))
    src = mstcn_dataset_dir(cfg, dataset)
    if not src.exists():
        # 尝试 extracted 子目录
        alt = ROOT / "data/features/mstcn_zenodo/extracted/data" / dataset
        src = alt if alt.exists() else src
    if not src.exists():
        print(f"source missing: {src}", file=sys.stderr)
        sys.exit(1)
    dst_root = protas_root(cfg) / "data"
    dst_root.mkdir(parents=True, exist_ok=True)
    dst = dst_root / dataset
    if dst.exists():
        print(f"dest exists: {dst}")
        return
    print(f"{src} -> {dst}")
    if args.copy:
        shutil.copytree(src, dst)
    else:
        try:
            dst.symlink_to(src.resolve(), target_is_directory=True)
        except OSError:
            print("symlink failed, falling back to copy")
            shutil.copytree(src, dst)
    print("ok")


if __name__ == "__main__":
    main()
