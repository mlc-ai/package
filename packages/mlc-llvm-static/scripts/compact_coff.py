"""Remove unneeded COFF symbols with LLVM's relocation-aware object copier."""
from __future__ import annotations

import json
import os
from pathlib import Path
import shutil
import subprocess

from prepare_llvm import sha256


def compact_coff(raw: Path) -> None:
    metadata_path = raw / "staticlib.json"
    metadata = json.loads(metadata_path.read_text())
    if metadata["system"] != "Windows":
        return
    executable = os.environ.get("MLC_LLVM_STATIC_OBJCOPY") or shutil.which("llvm-objcopy")
    if not executable:
        raise RuntimeError("Windows wheel packaging requires llvm-objcopy; set MLC_LLVM_STATIC_OBJCOPY to its path")
    version = subprocess.check_output([executable, "--version"], text=True).strip()
    if "LLVM" not in version:
        raise RuntimeError("MLC_LLVM_STATIC_OBJCOPY must be LLVM's llvm-objcopy")
    print(version, flush=True)
    before = after = 0
    prefix = raw / "static"
    for archive in sorted((prefix / "lib").glob("*.lib")):
        before += archive.stat().st_size
        # Unlike --strip-all, this retains external definitions, symbols used
        # by relocations, and COFF COMDAT associations. Code, data, relocations,
        # and unwind sections remain available to downstream native linkers.
        subprocess.run([executable, "--strip-unneeded", str(archive)], check=True)
        after += archive.stat().st_size
        metadata["files"][archive.relative_to(prefix).as_posix()] = {
            "sha256": sha256(archive), "size": archive.stat().st_size,
        }
    # The split build fingerprint includes both the transformation and the
    # resulting archive hashes, so compacted and original SDKs cannot be mixed.
    metadata["packaging"] = {"coff": "strip-unneeded", "llvm_objcopy": version}
    metadata_path.write_text(json.dumps(metadata, indent=2) + "\n")
    print(f"COFF archives: {before:,} -> {after:,} bytes", flush=True)
