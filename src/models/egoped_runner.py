"""EgoPED / EgoPER 上游入口提示与命令构造。"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from typing import Any

from src.data.paths import egoper_root


def run_egoped_help(cfg: dict[str, Any]) -> int:
    root = egoper_root(cfg)
    if not root.exists():
        raise FileNotFoundError(
            f"EgoPER repo missing: {root}. Run scripts/clone_third_party.py"
        )
    readme = root / "README.md"
    print(f"EgoPED code root: {root}")
    if readme.exists():
        print("--- README (head) ---")
        lines = readme.read_text(encoding="utf-8", errors="ignore").splitlines()[:40]
        print("\n".join(lines))
    print(
        "Enable datasets.egoper after approval, place data under data/public/egoper, "
        "then follow upstream train scripts."
    )
    return 0


def try_run_upstream_script(cfg: dict[str, Any], script_rel: str, extra: list[str] | None = None) -> int:
    root = egoper_root(cfg)
    script = root / script_rel
    if not script.exists():
        print(f"script not found: {script}")
        return run_egoped_help(cfg)
    cmd = [sys.executable, str(script)] + (extra or [])
    print("+", " ".join(cmd))
    return subprocess.call(cmd, cwd=str(root))
