#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = ROOT / "config.json"


def free_gb(path: Path) -> float:
    return shutil.disk_usage(path).free / (1024**3)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--path", type=Path, default=ROOT)
    args = parser.parse_args()
    target = args.path.resolve()
    free = free_gb(target)
    total = shutil.disk_usage(target).total / (1024**3)
    print(f"path={target}")
    print(f"free_gb={free:.1f}")
    print(f"total_gb={total:.1f}")

    if not CONFIG_PATH.exists():
        print("config=missing")
        return
    cfg = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    plan = cfg.get("download_plan", {})
    print(f"mode={cfg.get('mode')} active_tier={plan.get('active_tier')}")
    for name, tier in plan.get("tiers", {}).items():
        need = float(tier.get("min_free_gb", 0))
        flag = "ok" if free >= need else "no"
        print(f"tier={name} need_free_gb>={need} est_gb={tier.get('est_gb')} {flag}")


if __name__ == "__main__":
    main()
