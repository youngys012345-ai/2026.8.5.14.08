#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
模块一：下载数据（含上游代码克隆）

用法：
  python scripts/download_data.py          # 仅打印计划（design 模式）
  python scripts/download_data.py --run    # 真正执行（需 config.mode=run）

config 可调：mode, download_tier(T1|T3)
"""
from __future__ import annotations

import argparse
import json
import logging
import subprocess
import sys
import urllib.request
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CFG_PATH = ROOT / "config.json"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("download")

# 固定资源（一般不必改；要改就改本文件）
REPOS = {
    "ProTAS": "https://github.com/Yuhan-Shen/ProTAS.git",
    "EgoPER": "https://github.com/robert80203/EgoPER_official.git",
    "IndustReal": "https://github.com/TimSchoonbeek/IndustReal.git",
}

# T1：公开可获取，先跑通；T3：Assembly101 特征（跨视角）
TIERS = {
    "T1": [
        {
            "name": "mstcn_features",
            "url": "https://zenodo.org/records/3625992/files/data.zip?download=1",
            "dest": ROOT / "data/features/mstcn_zenodo/data.zip",
            "extract_to": ROOT / "data/features/mstcn_zenodo/extracted",
        },
        {
            "name": "industreal_manual",
            "page": "https://data.4tu.nl/datasets/b008dd74-020d-4ea4-a8ba-7bb60769d224",
            "hint": "请从页面下载 all_rgb_videos.zip 与 action_recognition_labels.zip 到 data/public/industreal/",
        },
    ],
    "T3": [
        {
            "name": "assembly101_features",
            "hf_repo": "cvml-nus/assembly101",
            "hf_patterns": ["TSM_features/**", "annotations/**"],
            "dest": ROOT / "data/features/assembly101",
        },
    ],
}


def load_cfg() -> dict:
    # _help 等以下划线开头的键仅为注释说明，不影响逻辑
    return json.loads(CFG_PATH.read_text(encoding="utf-8"))


def clone_repos(do_run: bool) -> None:
    tp = ROOT / "third_party"
    tp.mkdir(parents=True, exist_ok=True)
    for name, url in REPOS.items():
        path = tp / name
        if path.exists() and any(path.iterdir()):
            log.info("已存在，跳过克隆: %s", path)
            continue
        cmd = ["git", "clone", "--depth", "1", url, str(path)]
        log.info("克隆: %s", " ".join(cmd))
        if do_run:
            subprocess.check_call(cmd)


def download_file(url: str, dest: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.exists() and dest.stat().st_size > 0:
        log.info("已存在，跳过下载: %s", dest)
        return
    log.info("下载 %s -> %s", url, dest)
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=600) as resp, open(dest, "wb") as f:
        while True:
            chunk = resp.read(1024 * 1024)
            if not chunk:
                break
            f.write(chunk)


def extract_zip(zip_path: Path, out_dir: Path) -> None:
    marker = out_dir / ".ok"
    if marker.exists():
        log.info("已解压，跳过: %s", out_dir)
        return
    log.info("解压 %s -> %s", zip_path, out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(zip_path, "r") as zf:
        zf.extractall(out_dir)
    marker.write_text("ok", encoding="utf-8")


def link_gtea_to_protas() -> None:
    """把 GTEA 特征目录挂到 ProTAS/data/gtea，方便训练。"""
    candidates = [
        ROOT / "data/features/mstcn_zenodo/extracted/data/gtea",
        ROOT / "data/features/mstcn_zenodo/extracted/gtea",
        ROOT / "data/features/mstcn_zenodo/data/gtea",
    ]
    src = next((p for p in candidates if p.exists()), None)
    if src is None:
        log.warning("未找到 gtea 目录，训练前请确认 T1 已解压")
        return
    dst = ROOT / "third_party/ProTAS/data/gtea"
    dst.parent.mkdir(parents=True, exist_ok=True)
    if dst.exists():
        log.info("ProTAS 数据链接已存在: %s", dst)
        return
    try:
        dst.symlink_to(src.resolve(), target_is_directory=True)
        log.info("已链接 %s -> %s", src, dst)
    except OSError as e:
        log.error("创建符号链接失败，请手动拷贝数据: %s", e)
        raise


def download_hf(repo: str, patterns: list[str], dest: Path) -> None:
    from huggingface_hub import snapshot_download

    dest.mkdir(parents=True, exist_ok=True)
    log.info("HuggingFace 拉取 %s -> %s", repo, dest)
    snapshot_download(
        repo_id=repo,
        repo_type="dataset",
        local_dir=str(dest),
        allow_patterns=patterns,
        local_dir_use_symlinks=False,
    )


def run_tier(tier: str, do_run: bool) -> None:
    items = TIERS.get(tier)
    if not items:
        raise SystemExit(f"未知 download_tier={tier}，仅支持 T1 / T3")
    for item in items:
        name = item["name"]
        if "page" in item:
            log.info("[%s] 需手工下载: %s", name, item["page"])
            log.info("  %s", item.get("hint", ""))
            (ROOT / "data/public/industreal").mkdir(parents=True, exist_ok=True)
            continue
        if "hf_repo" in item:
            log.info("[%s] HF: %s patterns=%s", name, item["hf_repo"], item["hf_patterns"])
            if do_run:
                download_hf(item["hf_repo"], item["hf_patterns"], item["dest"])
            continue
        log.info("[%s] URL: %s", name, item["url"])
        if do_run:
            download_file(item["url"], item["dest"])
            if "extract_to" in item:
                extract_zip(item["dest"], item["extract_to"])


def main() -> None:
    parser = argparse.ArgumentParser(description="下载数据模块")
    parser.add_argument("--run", action="store_true", help="真正执行；默认只打印计划")
    args = parser.parse_args()

    cfg = load_cfg()
    tier = str(cfg.get("download_tier", "T1")).upper()
    do_run = bool(args.run)
    if do_run and cfg.get("mode") != "run":
        raise SystemExit("拒绝执行：请先在 config.json 将 mode 设为 run")

    log.info("mode=%s tier=%s execute=%s", cfg.get("mode"), tier, do_run)
    for d in ["data/public", "data/features", "data/internal", "outputs", "third_party"]:
        (ROOT / d).mkdir(parents=True, exist_ok=True)

    clone_repos(do_run)
    run_tier(tier, do_run)
    if do_run and tier == "T1":
        link_gtea_to_protas()

    if not do_run:
        log.info("当前为计划模式。内网执行: 改 mode=run 后加 --run")


if __name__ == "__main__":
    try:
        main()
    except Exception:
        log.exception("下载模块失败")
        sys.exit(1)
