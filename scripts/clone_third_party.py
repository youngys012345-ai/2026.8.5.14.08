#!/usr/bin/env python3
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
YAML_PATH = ROOT / "resources" / "datasets.yaml"


def main() -> None:
    try:
        import yaml
    except ImportError:
        print("pyyaml required", file=sys.stderr)
        sys.exit(1)

    if not YAML_PATH.exists():
        print(f"missing {YAML_PATH} (local only, not in git)", file=sys.stderr)
        sys.exit(1)

    data = yaml.safe_load(YAML_PATH.read_text(encoding="utf-8"))
    repos = (data or {}).get("third_party", {})
    root_tp = ROOT / "third_party"
    root_tp.mkdir(parents=True, exist_ok=True)

    for _name, meta in repos.items():
        url = meta["url"]
        path = ROOT / meta["path"]
        if path.exists() and any(path.iterdir()):
            print(f"skip {path}")
            continue
        path.parent.mkdir(parents=True, exist_ok=True)
        cmd = ["git", "clone", "--depth", "1", url, str(path)]
        print("+", " ".join(cmd))
        subprocess.run(cmd, check=True)


if __name__ == "__main__":
    main()
