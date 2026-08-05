#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

DIRS = [
    ROOT / "data" / "public",
    ROOT / "data" / "features",
    ROOT / "data" / "internal",
    ROOT / "outputs",
    ROOT / "third_party",
]


def main() -> None:
    for path in DIRS:
        path.mkdir(parents=True, exist_ok=True)
        if path.name in {"public", "features", "internal", "third_party"}:
            if not any(path.iterdir()):
                (path / ".gitkeep").touch(exist_ok=True)
        print(f"[ok] {path.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
