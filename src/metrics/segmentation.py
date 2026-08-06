"""动作分割常用指标：帧准确率、Edit、F1@IoU、边界误差。"""
from __future__ import annotations

from collections import defaultdict
from typing import Iterable, Sequence


def frame_accuracy(pred: Sequence[int], gt: Sequence[int]) -> float:
    n = min(len(pred), len(gt))
    if n == 0:
        return 0.0
    return sum(int(pred[i] == gt[i]) for i in range(n)) / n


def _to_segments(labels: Sequence[int]) -> list[tuple[int, int, int]]:
    """返回 (start, end_exclusive, class_id) 段列表。"""
    if not labels:
        return []
    segs: list[tuple[int, int, int]] = []
    start = 0
    cur = labels[0]
    for i in range(1, len(labels)):
        if labels[i] != cur:
            segs.append((start, i, int(cur)))
            start = i
            cur = labels[i]
    segs.append((start, len(labels), int(cur)))
    return segs


def levenstein(pred: Sequence[int], gt: Sequence[int]) -> float:
    """段级编辑距离相似度 Edit（与 MS-TCN 常用定义一致的归一化版本）。"""
    p = [s[2] for s in _to_segments(pred)]
    g = [s[2] for s in _to_segments(gt)]
    if len(p) == 0 and len(g) == 0:
        return 1.0
    m, n = len(p), len(g)
    dp = [[0] * (n + 1) for _ in range(m + 1)]
    for i in range(m + 1):
        dp[i][0] = i
    for j in range(n + 1):
        dp[0][j] = j
    for i in range(1, m + 1):
        for j in range(1, n + 1):
            cost = 0 if p[i - 1] == g[j - 1] else 1
            dp[i][j] = min(dp[i - 1][j] + 1, dp[i][j - 1] + 1, dp[i - 1][j - 1] + cost)
    dist = dp[m][n]
    return 1.0 - dist / max(m, n)


def _iou(a: tuple[int, int, int], b: tuple[int, int, int]) -> float:
    inter = max(0, min(a[1], b[1]) - max(a[0], b[0]))
    union = max(a[1], b[1]) - min(a[0], b[0])
    return inter / union if union > 0 else 0.0


def f1_at_iou(pred: Sequence[int], gt: Sequence[int], thr: float) -> float:
    ps = _to_segments(pred)
    gs = _to_segments(gt)
    if not gs:
        return 1.0 if not ps else 0.0
    hits = 0
    used = set()
    for g in gs:
        best_j, best = -1, 0.0
        for j, p in enumerate(ps):
            if j in used or p[2] != g[2]:
                continue
            v = _iou(p, g)
            if v > best:
                best, best_j = v, j
        if best >= thr and best_j >= 0:
            hits += 1
            used.add(best_j)
    precision = hits / len(ps) if ps else 0.0
    recall = hits / len(gs) if gs else 0.0
    if precision + recall == 0:
        return 0.0
    return 2 * precision * recall / (precision + recall)


def boundary_mae_frames(pred: Sequence[int], gt: Sequence[int]) -> float:
    """比较相邻段边界位置的平均绝对误差（帧）。"""
    pb = [s[0] for s in _to_segments(pred)[1:]]
    gb = [s[0] for s in _to_segments(gt)[1:]]
    if not gb:
        return 0.0
    # 贪婪按顺序对齐到较短一侧
    n = min(len(pb), len(gb))
    if n == 0:
        return float(sum(gb) / len(gb)) if not pb else float("inf")
    return sum(abs(pb[i] - gb[i]) for i in range(n)) / n


def boundary_delta_accuracy(
    pred: Sequence[int], gt: Sequence[int], delta_frames: int
) -> float:
    pb = [s[0] for s in _to_segments(pred)[1:]]
    gb = [s[0] for s in _to_segments(gt)[1:]]
    if not gb:
        return 1.0
    n = min(len(pb), len(gb))
    if n == 0:
        return 0.0
    return sum(abs(pb[i] - gb[i]) <= delta_frames for i in range(n)) / len(gb)


def overseg_ratio(pred: Sequence[int], gt: Sequence[int]) -> float:
    ps = len(_to_segments(pred))
    gs = len(_to_segments(gt))
    return ps / gs if gs else float(ps)


def sequence_edit_distance(pred_steps: Sequence[str], gt_steps: Sequence[str]) -> float:
    """步骤串归一化编辑距离（越小越好）。"""
    m, n = len(pred_steps), len(gt_steps)
    if m == 0 and n == 0:
        return 0.0
    dp = [[0] * (n + 1) for _ in range(m + 1)]
    for i in range(m + 1):
        dp[i][0] = i
    for j in range(n + 1):
        dp[0][j] = j
    for i in range(1, m + 1):
        for j in range(1, n + 1):
            cost = 0 if pred_steps[i - 1] == gt_steps[j - 1] else 1
            dp[i][j] = min(dp[i - 1][j] + 1, dp[i][j - 1] + 1, dp[i - 1][j - 1] + cost)
    return dp[m][n] / max(m, n)


def evaluate_video(
    pred: Sequence[int],
    gt: Sequence[int],
    fps: float = 15.0,
    boundary_deltas_sec: Iterable[float] = (0.5, 1.0, 2.0),
) -> dict[str, float]:
    out: dict[str, float] = {
        "frame_acc": frame_accuracy(pred, gt),
        "edit": levenstein(pred, gt),
        "f1_0.1": f1_at_iou(pred, gt, 0.1),
        "f1_0.25": f1_at_iou(pred, gt, 0.25),
        "f1_0.5": f1_at_iou(pred, gt, 0.5),
        "boundary_mae_frames": boundary_mae_frames(pred, gt),
        "overseg_ratio": overseg_ratio(pred, gt),
    }
    for sec in boundary_deltas_sec:
        df = max(1, int(round(sec * fps)))
        out[f"boundary_delta_acc_{sec}s"] = boundary_delta_accuracy(pred, gt, df)
    return out


def aggregate_metrics(per_video: list[dict[str, float]]) -> dict[str, float]:
    if not per_video:
        return {}
    keys = per_video[0].keys()
    acc: dict[str, list[float]] = defaultdict(list)
    for row in per_video:
        for k in keys:
            acc[k].append(float(row[k]))
    return {k: sum(v) / len(v) for k, v in acc.items()}
