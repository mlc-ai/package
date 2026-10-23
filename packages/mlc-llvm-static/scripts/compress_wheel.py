#!/usr/bin/env python3
"""Use maximum standard DEFLATE compression without changing wheel contents."""
from __future__ import annotations

import argparse
from datetime import datetime
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import zipfile


def compress_wheel(wheel: Path) -> None:
    # Retagging with `wheel tags` recompresses the archive with default settings,
    # so apply this after all metadata/tag changes. RECORD hashes the unpacked
    # bytes; keeping every member unchanged also keeps all its hashes valid.
    temporary = wheel.with_suffix(".whl.tmp")
    try:
        if wheel.name.endswith("-win_amd64.whl"):
            compress_windows(wheel, temporary)
            temporary.replace(wheel)
            return
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


def compress_windows(wheel: Path, destination: Path) -> None:
    executable = os.environ.get("MLC_LLVM_STATIC_7ZIP") or shutil.which("7z") or shutil.which("7zz")
    if not executable:
        raise RuntimeError("Windows wheel packaging requires 7-Zip; set MLC_LLVM_STATIC_7ZIP to its path")
    with tempfile.TemporaryDirectory(prefix="llvm-wheel-deflate-") as temporary:
        work = Path(temporary)
        payload = work / "payload"
        with zipfile.ZipFile(wheel) as source:
            names = [member.filename for member in source.infolist() if not member.is_dir()]
            source.extractall(payload)
            for member in source.infolist():
                stamp = datetime(*member.date_time).timestamp()
                os.utime(payload / member.filename, (stamp, stamp))
            listing = work / "files.txt"
            listing.write_text("\n".join(names) + "\n", encoding="utf-8")
            output = work / "wheel.zip"
            subprocess.run([executable, "a", "-tzip", "-mm=Deflate", "-mx=9", "-mfb=258",
                            "-mpass=3", "-mmt=2", "-scsUTF-8", "-bd", "-bb0", "-y",
                            str(output), "@" + str(listing)], cwd=payload, check=True, timeout=1200)
            with zipfile.ZipFile(output, "a") as target:
                if set(target.namelist()) != set(source.namelist()):
                    raise RuntimeError("7-Zip changed the wheel member list")
                for member in target.infolist():
                    original = source.getinfo(member.filename)
                    if member.compress_type not in (zipfile.ZIP_STORED, zipfile.ZIP_DEFLATED):
                        raise RuntimeError("Only standard STORE/DEFLATE wheel compression is allowed")
                    if (member.CRC, member.file_size) != (original.CRC, original.file_size):
                        raise RuntimeError(f"7-Zip changed wheel payload: {member.filename}")
                    member.external_attr = original.external_attr
                    member.internal_attr = original.internal_attr
                    member.create_system = original.create_system
                    member.date_time = original.date_time
                    member.comment = original.comment
                # This public setter also requests a central-directory rewrite,
                # preserving original modes/times without recompressing payloads.
                target.comment = source.comment
            shutil.copy2(output, destination)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("wheels", nargs="+", type=Path)
    for path in parser.parse_args().wheels:
        before = path.stat().st_size
        compress_wheel(path)
        print(f"{path.name}: {before:,} -> {path.stat().st_size:,} bytes", flush=True)
