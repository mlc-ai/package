#!/usr/bin/env python3
"""Use maximum standard DEFLATE compression without changing wheel contents."""
from __future__ import annotations

import argparse
from pathlib import Path
import zipfile


def compress_wheel(wheel: Path) -> None:
    # Retagging with `wheel tags` recompresses the archive with default settings,
    # so apply this after all metadata/tag changes. RECORD hashes the unpacked
    # bytes; keeping every member unchanged also keeps all its hashes valid.
    temporary = wheel.with_suffix(".whl.tmp")
    try:
        with zipfile.ZipFile(wheel) as source, zipfile.ZipFile(
            temporary, "w", zipfile.ZIP_DEFLATED, compresslevel=9,
        ) as destination:
            destination.comment = source.comment
            for member in source.infolist():
                destination.writestr(member, source.read(member),
                                     compress_type=zipfile.ZIP_DEFLATED, compresslevel=9)
        temporary.replace(wheel)
    finally:
        temporary.unlink(missing_ok=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("wheels", nargs="+", type=Path)
    for path in parser.parse_args().wheels:
        before = path.stat().st_size
        compress_wheel(path)
        print(f"{path.name}: {before:,} -> {path.stat().st_size:,} bytes", flush=True)
