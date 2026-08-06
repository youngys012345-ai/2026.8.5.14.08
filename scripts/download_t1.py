#!/usr/bin/env python3
"""T1：Zenodo MS-TCN 特征包 + IndustReal（公开可获取）。"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from download_tier import run_tier  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description="Download plan/execute for T1_bootstrap")
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    execute = bool(args.execute) and not args.dry_run
    raise SystemExit(run_tier("T1_bootstrap", execute=execute))


if __name__ == "__main__":
    main()
