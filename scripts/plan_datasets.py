#!/usr/bin/env python3
"""Print dataset download plan from config.json (no network I/O)."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = ROOT / "config.json"


def main() -> None:
    cfg = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    plan = cfg.get("download_plan", {})
    datasets = cfg.get("datasets", {})
    tier_name = plan.get("active_tier", "")
    tiers = plan.get("tiers", {})
    tier = tiers.get(tier_name, {})

    print(f"mode={cfg.get('mode')}")
    print(f"allow_download={plan.get('allow_download')}")
    print(f"active_tier={tier_name}")
    print(f"tier_est_gb={tier.get('est_gb')} min_free_gb={tier.get('min_free_gb')}")
    print("--- enabled dataset flags ---")
    for key, meta in sorted(datasets.items(), key=lambda kv: kv[1].get("priority", 99)):
        print(
            f"{key}: enabled={meta.get('enabled')} access={meta.get('access')} "
            f"status={meta.get('status')} est_gb={meta.get('est_gb')}"
        )
    print("--- tier item list ---")
    for item in tier.get("items", []):
        meta = datasets.get(item, {})
        mark = "ON" if meta.get("enabled") else "OFF"
        print(f"[{mark}] {item} -> {meta.get('target_dir')} page={meta.get('page')}")
        if meta.get("access") == "request":
            print(f"      request_email={meta.get('request_email')}")
    print("No files will be downloaded by this script.")


if __name__ == "__main__":
    main()
