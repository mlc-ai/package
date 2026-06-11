"""Copy a wheel into cibuildwheel's repaired wheel directory."""

from __future__ import annotations

import shutil
import sys
from pathlib import Path


def main() -> None:
    if len(sys.argv) != 3:
        raise SystemExit("Usage: copy_wheel.py WHEEL DEST_DIR")
    wheel = Path(sys.argv[1])
    dest = Path(sys.argv[2])
    dest.mkdir(parents=True, exist_ok=True)
    shutil.copy2(wheel, dest / wheel.name)


if __name__ == "__main__":
    main()

