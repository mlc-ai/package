#!/usr/bin/env python3
from __future__ import annotations

import shutil
import sys
from pathlib import Path


def main() -> None:
    if len(sys.argv) != 3:
        raise SystemExit("usage: copy_wheel.py <wheel> <dest-dir>")
    wheel = Path(sys.argv[1]).resolve()
    dest_dir = Path(sys.argv[2]).resolve()
    dest_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy2(wheel, dest_dir / wheel.name)


if __name__ == "__main__":
    main()
