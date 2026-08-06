"""读入 MS-TCN / ProTAS 风格的逐帧标签文件。"""
from __future__ import annotations

from pathlib import Path


def load_label_file(path: Path, actions_dict: dict[str, int] | None = None) -> list[int]:
    text = path.read_text(encoding="utf-8").strip().split("\n")
    labels: list[int] = []
    for line in text:
        line = line.strip()
        if not line:
            continue
        # 可能是类别名或整数
        if actions_dict is not None and line in actions_dict:
            labels.append(actions_dict[line])
        else:
            try:
                labels.append(int(line.split()[0]))
            except ValueError:
                if actions_dict is None:
                    raise
                # 未见映射则扩展
                actions_dict[line] = len(actions_dict)
                labels.append(actions_dict[line])
    return labels


def load_mapping(mapping_file: Path) -> dict[str, int]:
    actions: dict[str, int] = {}
    for line in mapping_file.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        # "0 action" 或 "0|action"
        if "|" in line:
            idx, name = line.split("|", 1)
        else:
            parts = line.split()
            idx, name = parts[0], parts[1]
        actions[name] = int(idx)
    return actions
