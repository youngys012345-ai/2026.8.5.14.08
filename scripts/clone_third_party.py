#!/usr/bin/env python3
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = ROOT / "config.json"


def main() -> None:
    cfg = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    if cfg.get("mode") == "design":
        print("mode=design: listing clone plan only (no git clone)")
        for name, meta in cfg.get("third_party", {}).items():
            print(
                f"{name}: enabled={meta.get('enabled')} "
                f"-> {meta.get('path')} url={meta.get('url')}"
            )
        print("Intranet: set mode=run then re-run to clone.")
        return

    root_tp = ROOT / cfg.get("paths", {}).get("third_party", "third_party")
    root_tp.mkdir(parents=True, exist_ok=True)
    for name, meta in cfg.get("third_party", {}).items():
        if not meta.get("enabled", True):
            print(f"skip disabled {name}")
            continue
        path = ROOT / meta["path"]
        if path.exists() and any(path.iterdir()):
            print(f"skip exists {path}")
            continue
        depth = str(meta.get("depth", 1))
        cmd = ["git", "clone", "--depth", depth, meta["url"], str(path)]
        print("+", " ".join(cmd))
        subprocess.run(cmd, check=True)


if __name__ == "__main__":
    main()
