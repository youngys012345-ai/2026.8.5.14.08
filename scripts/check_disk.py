#!/usr/bin/env python3
from __future__ import annotations

import argparse
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
YAML_PATH = ROOT / "resources" / "datasets.yaml"


def free_gb(path: Path) -> float:
    return shutil.disk_usage(path).free / (1024**3)


def load_tiers() -> dict:
    try:
        import yaml
    except ImportError:
        return {}
    if not YAML_PATH.exists():
        return {}
    data = yaml.safe_load(YAML_PATH.read_text(encoding="utf-8"))
    return data.get("tiers", {}) if data else {}


def recommend(free: float, tiers: dict) -> list[str]:
    ok = []
    for key, meta in tiers.items():
        need = float(meta.get("free_space_recommend_gb", 0))
        if free >= need:
            ok.append(key)
    return ok


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

    tiers = load_tiers()
    if not tiers:
        print("tiers=unavailable (missing local resources/datasets.yaml)")
        return
    ok = recommend(free, tiers)
    print("ok_tiers=" + (",".join(ok) if ok else "none"))
    for key, meta in tiers.items():
        est = meta.get("estimated_gb", ["?", "?"])
        need = meta.get("free_space_recommend_gb", "?")
        flag = "ok" if key in ok else "no"
        print(f"{key} est={est[0]}-{est[1]} need_free>={need} {flag}")


if __name__ == "__main__":
    main()
