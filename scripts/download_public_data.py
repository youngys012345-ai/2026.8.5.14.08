#!/usr/bin/env python3
"""兼容入口：转发到 download_tier。"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from download_tier import run_tier


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--tier", default=None)
    parser.add_argument("--only", nargs="*")
    args = parser.parse_args()
    import json

    cfg = json.loads(Path(__file__).resolve().parents[1].joinpath("config.json").read_text(encoding="utf-8"))
    tier = args.tier or cfg.get("download_plan", {}).get("active_tier", "T1_bootstrap")
    execute = bool(args.execute) and not args.dry_run
    raise SystemExit(run_tier(tier, execute=execute, only=args.only))


if __name__ == "__main__":
    main()
