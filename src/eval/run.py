"""评测入口：对预测标签与 GT 计算分割指标。"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from src.config_loader import load_config, resolve_path
from src.data.labels import load_label_file, load_mapping
from src.data.paths import mstcn_dataset_dir, ensure_data_dirs
from src.metrics.segmentation import aggregate_metrics, evaluate_video
from src.models.protas_runner import run_protas


def _collect_pairs(pred_dir: Path, gt_dir: Path) -> list[tuple[Path, Path]]:
    pairs = []
    for gt in sorted(gt_dir.glob("*")):
        if gt.suffix.lower() not in {".txt", ""} and not gt.is_file():
            continue
        if not gt.is_file():
            continue
        pred = pred_dir / gt.name
        if pred.exists():
            pairs.append((pred, gt))
    return pairs


def eval_prediction_dirs(
    pred_dir: Path,
    gt_dir: Path,
    mapping_file: Path | None,
    fps: float,
    boundary_deltas_sec: list[float],
) -> dict:
    actions = load_mapping(mapping_file) if mapping_file and mapping_file.exists() else None
    rows = []
    for pred_path, gt_path in _collect_pairs(pred_dir, gt_dir):
        pred = load_label_file(pred_path, actions)
        gt = load_label_file(gt_path, actions)
        m = evaluate_video(pred, gt, fps=fps, boundary_deltas_sec=boundary_deltas_sec)
        m["video"] = gt_path.name
        rows.append(m)
    summary = aggregate_metrics([{k: v for k, v in r.items() if k != "video"} for r in rows])
    return {"summary": summary, "per_video": rows}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Eval from config.json")
    parser.add_argument("--config", type=Path, default=None)
    parser.add_argument("--pred-dir", type=Path, default=None, help="预测标签目录")
    parser.add_argument("--gt-dir", type=Path, default=None, help="GT 标签目录")
    parser.add_argument("--run-upstream-predict", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--fps", type=float, default=15.0)
    args = parser.parse_args(argv)

    cfg = load_config(args.config)
    ensure_data_dirs(cfg)
    ev = cfg.get("eval", {})
    train = cfg.get("train", {})
    dataset = str(train.get("dataset", "gtea"))
    data_dir = mstcn_dataset_dir(cfg, dataset)
    gt_dir = args.gt_dir or (data_dir / "groundTruth")
    save_dir = resolve_path(cfg, "outputs") / "eval" / str(train.get("exp_id", "run0"))
    save_dir.mkdir(parents=True, exist_ok=True)

    if args.run_upstream_predict:
        if cfg.get("mode") != "run" and not args.dry_run:
            print("refusing predict: set mode=run")
            return 2
        if args.dry_run or cfg.get("mode") == "design":
            print("dry-run: would call ProTAS predict")
        else:
            code = run_protas(cfg, action="predict")
            if code != 0:
                return code

    pred_dir = args.pred_dir
    if pred_dir is None:
        # ProTAS 常见结果目录猜测；可用 --pred-dir 覆盖
        protas = Path(cfg.get("third_party", {}).get("ProTAS", {}).get("path", "third_party/ProTAS"))
        if not protas.is_absolute():
            from src.config_loader import project_root

            protas = project_root() / protas
        candidates = list(protas.glob(f"**/results/{dataset}/**"))
        pred_dir = candidates[0] if candidates else save_dir / "pred"
        print(f"pred_dir_guess={pred_dir}")

    if args.dry_run or cfg.get("mode") == "design":
        print(f"gt_dir={gt_dir}")
        print(f"pred_dir={pred_dir}")
        print("dry-run only")
        return 0

    if not gt_dir.exists():
        print(f"missing gt_dir: {gt_dir}")
        return 1
    if not Path(pred_dir).exists():
        print(f"missing pred_dir: {pred_dir}. Provide --pred-dir or --run-upstream-predict")
        return 1

    mapping = data_dir / "mapping.txt"
    result = eval_prediction_dirs(
        Path(pred_dir),
        gt_dir,
        mapping if mapping.exists() else None,
        fps=args.fps,
        boundary_deltas_sec=list(ev.get("boundary_deltas_sec", [0.5, 1.0, 2.0])),
    )
    out_json = save_dir / "metrics.json"
    out_json.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(result["summary"], ensure_ascii=False, indent=2))
    print(f"wrote {out_json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
