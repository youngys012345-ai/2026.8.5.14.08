#!/usr/bin/env python3
"""统一下载入口：按档位从 config.json 规划/执行。"""
from __future__ import annotations

import argparse
import json
import shutil
import sys
import urllib.request
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

CONFIG_PATH = ROOT / "config.json"


def load_config() -> dict:
    return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))


def free_gb(path: Path) -> float:
    return shutil.disk_usage(path).free / (1024**3)


def download_url(url: str, dest: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    print(f"GET {url}")
    print(f" -> {dest}")
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=600) as resp, open(dest, "wb") as out:
        total = resp.headers.get("Content-Length")
        total_i = int(total) if total else None
        done = 0
        while True:
            chunk = resp.read(1024 * 1024)
            if not chunk:
                break
            out.write(chunk)
            done += len(chunk)
            if total_i:
                print(f"\r  {done / 1e9:.2f}/{total_i / 1e9:.2f} GB", end="", flush=True)
            else:
                print(f"\r  {done / 1e9:.2f} GB", end="", flush=True)
        print()


def maybe_unzip(zip_path: Path, out_dir: Path) -> None:
    if not zip_path.exists() or zip_path.suffix.lower() != ".zip":
        return
    marker = out_dir / ".extracted"
    if marker.exists():
        print(f"already extracted: {out_dir}")
        return
    print(f"unzip {zip_path} -> {out_dir}")
    out_dir.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(zip_path, "r") as zf:
        zf.extractall(out_dir)
    marker.write_text("ok", encoding="utf-8")


def download_hf_folder(repo_id: str, allow_patterns: list[str], local_dir: Path) -> None:
    try:
        from huggingface_hub import snapshot_download
    except ImportError as exc:
        raise RuntimeError(
            "huggingface_hub not installed. pip install huggingface_hub"
        ) from exc
    local_dir.mkdir(parents=True, exist_ok=True)
    print(f"HF snapshot {repo_id} patterns={allow_patterns} -> {local_dir}")
    snapshot_download(
        repo_id=repo_id,
        repo_type="dataset",
        local_dir=str(local_dir),
        allow_patterns=allow_patterns,
        local_dir_use_symlinks=False,
    )


def run_tier(tier_key: str, execute: bool, only: list[str] | None = None) -> int:
    cfg = load_config()
    plan = cfg.get("download_plan", {})
    datasets = cfg.get("datasets", {})
    tier = plan.get("tiers", {}).get(tier_key)
    if not tier:
        print(f"unknown tier {tier_key}", file=sys.stderr)
        return 1

    keys = only or list(tier.get("items", []))
    free = free_gb(ROOT)
    need = float(tier.get("min_free_gb", plan.get("min_free_gb", 40)))
    print(f"tier={tier_key} execute={execute} free_gb={free:.1f} need>={need}")
    print(f"mode={cfg.get('mode')} allow_download={plan.get('allow_download')}")

    if execute:
        if cfg.get("mode") != "run":
            print("set mode=run in config.json", file=sys.stderr)
            return 2
        if not plan.get("allow_download", False):
            print("set download_plan.allow_download=true", file=sys.stderr)
            return 2
        if free < need:
            print(f"insufficient disk free_gb<{need}", file=sys.stderr)
            return 2

    for key in keys:
        meta = datasets.get(key)
        if not meta:
            print(f"unknown dataset {key}", file=sys.stderr)
            continue
        # 档位脚本强制处理该档 items；仍尊重 enabled=false 的跳过提示
        if not meta.get("enabled", False):
            print(f"WARN {key} enabled=false in config; skip (set enabled=true to download)")
            continue

        target_dir = ROOT / meta["target_dir"]
        filename = meta.get("filename") or f"{key}.bin"
        dest = target_dir / filename
        method = meta.get("download_method", "url")
        print(f"item={key} method={method} access={meta.get('access')} est_gb={meta.get('est_gb')}")
        print(f"  target={target_dir}")

        if method == "huggingface":
            repo_id = meta.get("hf_repo_id")
            patterns = meta.get("hf_allow_patterns", ["*"])
            if not execute:
                print(f"  dry-run HF {repo_id} patterns={patterns}")
                continue
            try:
                download_hf_folder(repo_id, patterns, target_dir)
            except Exception as exc:
                print(f"  HF fail: {exc}", file=sys.stderr)
                print(f"  manual page: {meta.get('page')}", file=sys.stderr)
            continue

        if method == "manual_page" or meta.get("access") != "public":
            print(f"  manual: open {meta.get('page')} and save to {target_dir}/{filename}")
            if meta.get("request_email"):
                print(f"  request_email={meta.get('request_email')}")
            continue

        url = (meta.get("url") or "").strip()
        if not url:
            print(f"  no url; open page {meta.get('page')}")
            continue
        if not execute:
            print(f"  dry-run GET {url} -> {dest}")
            continue
        if dest.exists() and dest.stat().st_size > 0 and cfg.get("options", {}).get("skip_if_exists", True):
            print("  skip exists")
        else:
            try:
                download_url(url, dest)
            except Exception as exc:
                print(f"  fail: {exc}", file=sys.stderr)
                print(f"  page: {meta.get('page')}", file=sys.stderr)
                continue
        if meta.get("auto_extract", False):
            maybe_unzip(dest, target_dir / "extracted")

    if not execute:
        print("Dry-run done. Intranet: mode=run, allow_download=true, re-run with --execute")
    return 0


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--tier", required=True, help="e.g. T1_bootstrap / T3_aux_crossview")
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--only", nargs="*")
    args = parser.parse_args()
    execute = bool(args.execute) and not args.dry_run
    raise SystemExit(run_tier(args.tier, execute=execute, only=args.only))


if __name__ == "__main__":
    main()
