#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
模块三：运行评测

用法：
  python scripts/eval.py                      # 计划 / 检查路径
  python scripts/eval.py --run                # 先让 ProTAS predict，再算指标
  python scripts/eval.py --run --pred-dir DIR # 只对已有预测目录算指标

config 可调：mode, gpu_id, dataset, split, exp_id, pred_dir
"""
from __future__ import annotations

import argparse
import json
import logging
import os
import subprocess
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CFG_PATH = ROOT / "config.json"
PROTAS = ROOT / "third_party" / "ProTAS"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("eval")


def load_cfg() -> dict:
    # config.json 中 _help 仅为说明，读取后按字段名使用即可
    return json.loads(CFG_PATH.read_text(encoding="utf-8"))


# ---------- 指标（自包含，避免再拆模块）----------

def _segments(labels: list[int]) -> list[tuple[int, int, int]]:
    if not labels:
        return []
    out, s, cur = [], 0, labels[0]
    for i in range(1, len(labels)):
        if labels[i] != cur:
            out.append((s, i, int(cur)))
            s, cur = i, labels[i]
    out.append((s, len(labels), int(cur)))
    return out


def frame_acc(pred: list[int], gt: list[int]) -> float:
    n = min(len(pred), len(gt))
    return 0.0 if n == 0 else sum(p == g for p, g in zip(pred[:n], gt[:n])) / n


def edit_score(pred: list[int], gt: list[int]) -> float:
    p = [x[2] for x in _segments(pred)]
    g = [x[2] for x in _segments(gt)]
    if not p and not g:
        return 1.0
    m, n = len(p), len(g)
    dp = [[0] * (n + 1) for _ in range(m + 1)]
    for i in range(m + 1):
        dp[i][0] = i
    for j in range(n + 1):
        dp[0][j] = j
    for i in range(1, m + 1):
        for j in range(1, n + 1):
            c = 0 if p[i - 1] == g[j - 1] else 1
            dp[i][j] = min(dp[i - 1][j] + 1, dp[i][j - 1] + 1, dp[i - 1][j - 1] + c)
    return 1.0 - dp[m][n] / max(m, n)


def f1_at(pred: list[int], gt: list[int], thr: float) -> float:
    ps, gs = _segments(pred), _segments(gt)
    if not gs:
        return 1.0 if not ps else 0.0
    hits, used = 0, set()
    for g in gs:
        best_j, best = -1, 0.0
        for j, p in enumerate(ps):
            if j in used or p[2] != g[2]:
                continue
            inter = max(0, min(p[1], g[1]) - max(p[0], g[0]))
            union = max(p[1], g[1]) - min(p[0], g[0])
            v = inter / union if union else 0.0
            if v > best:
                best, best_j = v, j
        if best >= thr and best_j >= 0:
            hits += 1
            used.add(best_j)
    prec = hits / len(ps) if ps else 0.0
    rec = hits / len(gs)
    return 0.0 if prec + rec == 0 else 2 * prec * rec / (prec + rec)


def load_label_file(path: Path) -> list[int]:
    """支持纯整数行，或类别名行（用 hash 稳定映射仅用于相对比较时请用 mapping）。"""
    mapping_path = path.parent.parent / "mapping.txt"
    name2id: dict[str, int] = {}
    if mapping_path.exists():
        for line in mapping_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            if "|" in line:
                i, name = line.split("|", 1)
            else:
                i, name = line.split(None, 1)
            name2id[name] = int(i)
    labels: list[int] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        tok = line.split()[0]
        if tok in name2id:
            labels.append(name2id[tok])
        else:
            try:
                labels.append(int(tok))
            except ValueError:
                name2id[tok] = len(name2id)
                labels.append(name2id[tok])
    return labels


def find_gt_dir(dataset: str) -> Path:
    cands = [
        PROTAS / "data" / dataset / "groundTruth",
        ROOT / "data/features/mstcn_zenodo/extracted/data" / dataset / "groundTruth",
        ROOT / "data/features/mstcn_zenodo/extracted" / dataset / "groundTruth",
    ]
    for p in cands:
        if p.exists():
            return p
    raise FileNotFoundError("找不到 groundTruth，请确认已下载并链接数据")


def find_pred_dir(cfg: dict, dataset: str) -> Path:
    if cfg.get("pred_dir"):
        return Path(cfg["pred_dir"])
    # 常见 ProTAS 结果路径猜测
    hits = list(PROTAS.glob(f"**/results/**/{dataset}/**"))
    hits += list(PROTAS.glob(f"**/results/{dataset}/**"))
    for h in hits:
        if h.is_dir() and any(h.iterdir()):
            return h
    raise FileNotFoundError(
        "找不到预测目录。请先训练并 predict，或在 config.pred_dir 填写路径。"
    )


def run_predict(cfg: dict) -> None:
    if not (PROTAS / "main.py").exists():
        raise FileNotFoundError("缺少 ProTAS")
    cmd = [
        sys.executable,
        "main.py",
        "--action",
        "predict",
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
    env = os.environ.copy()
    env["CUDA_VISIBLE_DEVICES"] = str(cfg.get("gpu_id", "0"))
    log.info("预测: %s", " ".join(cmd))
    code = subprocess.call(cmd, cwd=str(PROTAS), env=env)
    if code != 0:
        raise RuntimeError(f"predict 退出码 {code}")


def evaluate(pred_dir: Path, gt_dir: Path) -> dict:
    rows = []
    for gt in sorted(gt_dir.iterdir()):
        if not gt.is_file():
            continue
        pred = pred_dir / gt.name
        if not pred.exists():
            log.warning("缺预测文件: %s", pred.name)
            continue
        p, g = load_label_file(pred), load_label_file(gt)
        rows.append(
            {
                "video": gt.name,
                "frame_acc": frame_acc(p, g),
                "edit": edit_score(p, g),
                "f1_0.5": f1_at(p, g, 0.5),
            }
        )
    if not rows:
        raise RuntimeError("没有可评测的视频对，请检查 pred_dir / groundTruth")
    summary: dict[str, float] = {}
    keys = [k for k in rows[0] if k != "video"]
    for k in keys:
        summary[k] = sum(r[k] for r in rows) / len(rows)
    return {"summary": summary, "n_videos": len(rows), "per_video": rows}


def main() -> None:
    parser = argparse.ArgumentParser(description="评测模块")
    parser.add_argument("--run", action="store_true")
    parser.add_argument("--pred-dir", type=str, default="", help="覆盖 config.pred_dir")
    parser.add_argument("--skip-predict", action="store_true", help="不调用上游 predict")
    args = parser.parse_args()

    cfg = load_cfg()
    if args.pred_dir:
        cfg["pred_dir"] = args.pred_dir
    dataset = str(cfg.get("dataset", "gtea"))

    if not args.run:
        log.info("计划模式 dataset=%s exp_id=%s", dataset, cfg.get("exp_id"))
        log.info("内网执行: mode=run 后加 --run")
        return

    if cfg.get("mode") != "run":
        raise SystemExit("拒绝评测：请先在 config.json 将 mode 设为 run")

    if not args.skip_predict and not cfg.get("pred_dir"):
        run_predict(cfg)

    gt_dir = find_gt_dir(dataset)
    pred_dir = find_pred_dir(cfg, dataset)
    log.info("gt=%s", gt_dir)
    log.info("pred=%s", pred_dir)
    result = evaluate(pred_dir, gt_dir)
    out = ROOT / "outputs" / "eval" / str(cfg.get("exp_id", "run0"))
    out.mkdir(parents=True, exist_ok=True)
    out_json = out / "metrics.json"
    out_json.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    log.info("summary=%s", result["summary"])
    log.info("已写入 %s", out_json)


if __name__ == "__main__":
    try:
        main()
    except Exception:
        log.exception("评测模块失败")
        sys.exit(1)
