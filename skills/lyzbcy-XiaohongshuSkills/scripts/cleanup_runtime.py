#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from datetime import datetime, timedelta
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
SKILL_DIR = SCRIPT_DIR.parent
RUNTIME_DIR = SKILL_DIR / "runtime"


def cleanup_folder(folder: Path, days: int) -> int:
    if not folder.exists():
        return 0
    cutoff = datetime.now() - timedelta(days=days)
    removed = 0
    for path in folder.iterdir():
        if not path.is_file():
            continue
        if datetime.fromtimestamp(path.stat().st_mtime) < cutoff:
            path.unlink(missing_ok=True)
            removed += 1
    return removed


def main():
    removed = 0
    removed += cleanup_folder(RUNTIME_DIR / "input", 7)
    removed += cleanup_folder(RUNTIME_DIR / "qrcode", 3)
    removed += cleanup_folder(RUNTIME_DIR / "screenshots", 7)
    print(f"cleanup_removed={removed}")


if __name__ == "__main__":
    main()