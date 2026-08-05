#!/usr/bin/env python3
from __future__ import annotations

import argparse
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

    parser = argparse.ArgumentParser()
    parser.add_argument("--tier", default="S0_minimal")
    args = parser.parse_args()

    data = yaml.safe_load(YAML_PATH.read_text(encoding="utf-8"))
    tiers = (data or {}).get("tiers", {})
    datasets = (data or {}).get("datasets", {})

    if args.tier not in tiers:
        print(f"unknown tier: {args.tier}", file=sys.stderr)
        print("candidates:", ", ".join(tiers.keys()), file=sys.stderr)
        sys.exit(1)

    tier = tiers[args.tier]
    print(f"tier={args.tier}")
    print(f"estimated_gb={tier.get('estimated_gb')}")
    print(f"free_space_recommend_gb={tier.get('free_space_recommend_gb')}")
    for item_id in tier.get("items", []):
        meta = datasets.get(item_id, {})
        print(f"item={item_id}")
        print(f"  form={meta.get('form')}")
        print(f"  size_gb_est={meta.get('size_gb_est')}")
        for url in meta.get("urls", []) or []:
            print(f"  url={url}")
        if meta.get("request_email"):
            print(f"  email={meta['request_email']}")


if __name__ == "__main__":
    main()
