#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
模块二：运行训练

用法：
  python scripts/train.py           # 打印将执行的命令
  python scripts/train.py --run     # 真正训练（需 mode=run，且已 download）

config 可调：mode, gpu_id, dataset, split, exp_id, epochs
依赖：third_party/ProTAS 与对应数据集特征（见 download_data.py）
"""
from __future__ import annotations

import argparse
import json
import logging
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CFG_PATH = ROOT / "config.json"
PROTAS = ROOT / "third_party" / "ProTAS"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("train")


def load_cfg() -> dict:
    # config.json 中 _help 仅为说明，读取后按字段名使用即可
    return json.loads(CFG_PATH.read_text(encoding="utf-8"))


def ensure_ready(dataset: str) -> None:
    if not (PROTAS / "main.py").exists():
        raise FileNotFoundError("缺少 ProTAS，请先运行: python scripts/download_data.py --run")
    data_dir = PROTAS / "data" / dataset
    if not data_dir.exists():
        raise FileNotFoundError(
            f"缺少数据目录 {data_dir}。请先完成 T1 下载，或手动把特征放到该路径。"
        )


def build_cmd(cfg: dict) -> list[str]:
    # 上游 ProTAS 入口；开关按论文默认打开 causal/graph
    return [
        sys.executable,
        "main.py",
        "--action",
        "train",
        "--dataset",
        str(cfg.get("dataset", "gtea")),
        "--split",
        str(cfg.get("split", "1")),
        "--exp_id",
        str(cfg.get("exp_id", "run0")),
        "--causal",
        "--graph",
        "--learnable_graph",
    ]


def main() -> None:
    parser = argparse.ArgumentParser(description="训练模块")
    parser.add_argument("--run", action="store_true")
    args = parser.parse_args()

    cfg = load_cfg()
    dataset = str(cfg.get("dataset", "gtea"))
    cmd = build_cmd(cfg)
    log.info("将在 %s 执行: %s", PROTAS, " ".join(cmd))
    log.info("gpu_id=%s epochs(config备忘)=%s", cfg.get("gpu_id"), cfg.get("epochs"))

    if not args.run:
        log.info("计划模式。内网执行: mode=run 后加 --run")
        return

    if cfg.get("mode") != "run":
        raise SystemExit("拒绝训练：请先在 config.json 将 mode 设为 run")

    ensure_ready(dataset)
    env = os.environ.copy()
    env["CUDA_VISIBLE_DEVICES"] = str(cfg.get("gpu_id", "0"))
    # 部分上游脚本用 num_epochs 等参数；若报错 unrecognized，以 ProTAS README 为准改本文件命令
    code = subprocess.call(cmd, cwd=str(PROTAS), env=env)
    if code != 0:
        raise SystemExit(f"训练进程退出码 {code}，请向上滚动查看上游报错")
    log.info("训练结束")


if __name__ == "__main__":
    try:
        main()
    except Exception:
        log.exception("训练模块失败")
        sys.exit(1)
