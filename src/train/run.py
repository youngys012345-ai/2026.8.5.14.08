"""训练入口：按 config.train.backend 调度。"""
from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path

from src.config_loader import load_config, project_root, resolve_path
from src.data.paths import ensure_data_dirs
from src.models.egoped_runner import run_egoped_help
from src.models.protas_runner import run_protas


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Train from config.json")
    parser.add_argument("--config", type=Path, default=None)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)

    cfg = load_config(args.config)
    ensure_data_dirs(cfg)

    if cfg.get("mode") != "run" and not args.dry_run:
        print("refusing train: set config mode=run (or pass --dry-run to print plan)")
        return 2

    train = cfg.get("train", {})
    backend = train.get("backend", "ProTAS")
    print(f"backend={backend} dataset={train.get('dataset')} split={train.get('split')}")
    print(f"exp_id={train.get('exp_id')} epochs={train.get('epochs')}")

    out_dir = resolve_path(cfg, "outputs") / "train" / str(train.get("exp_id", "run0"))
    out_dir.mkdir(parents=True, exist_ok=True)
    snap = out_dir / f"config_snapshot_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    snap.write_text(json.dumps(cfg, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"config_snapshot={snap}")

    if args.dry_run or cfg.get("mode") == "design":
        print("dry-run only; no training launched")
        return 0

    if backend == "ProTAS":
        return run_protas(cfg, action="train")
    if backend in {"EgoPED", "EgoPER"}:
        return run_egoped_help(cfg)
    print(f"unknown backend: {backend}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
