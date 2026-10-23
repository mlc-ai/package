"""Fetch a checksum-pinned packaging tool; consumers never need this tool."""
from __future__ import annotations

import hashlib
import os
from pathlib import Path
import platform
import shutil
import tarfile
import urllib.request

SEVEN_ZIP_VERSION = "26.05"
SEVEN_ZIP = {
    ("Linux", "x86_64"): ("7z2605-linux-x64.tar.xz", "7zzs",
                          "22cf82fcc6eb7474f1d5bb4f02c0f8ebd573a718089d6833dc30f8350a3b232e"),
    ("Linux", "aarch64"): ("7z2605-linux-arm64.tar.xz", "7zzs",
                           "0b71f6cfc34669b3bf69f2347efd3429f77020665003a13b9cdc53b784270421"),
    ("Darwin", "arm64"): ("7z2605-mac.tar.xz", "7zz",
                          "12ef6830317743cfd3f0ab1724bde43fcc270d8b6d8564f8c12c2a2b7f993570"),
}


def seven_zip(work: Path) -> str:
    override = os.environ.get("MLC_LLVM_STATIC_7ZIP")
    if override:
        return shutil.which(override) or str(Path(override).resolve())
    host = (platform.system(), platform.machine().lower())
    if host[0] == "Windows":
        executable = shutil.which("7z") or shutil.which("7zz")
        if not executable:
            raise RuntimeError("Install 7-Zip or set MLC_LLVM_STATIC_7ZIP for wheel packaging")
        return executable
    if host not in SEVEN_ZIP:
        raise RuntimeError(f"Set MLC_LLVM_STATIC_7ZIP for unsupported packaging host {host}")
    filename, member, expected = SEVEN_ZIP[host]
    work.mkdir(parents=True, exist_ok=True)
    archive = work / filename
    if not archive.is_file() or hashlib.sha256(archive.read_bytes()).hexdigest() != expected:
        temporary = archive.with_suffix(".part")
        try:
            url = f"https://github.com/ip7z/7zip/releases/download/{SEVEN_ZIP_VERSION}/{filename}"
            with urllib.request.urlopen(url, timeout=120) as response, temporary.open("wb") as output:
                shutil.copyfileobj(response, output)
            if hashlib.sha256(temporary.read_bytes()).hexdigest() != expected:
                raise RuntimeError(f"7-Zip archive checksum mismatch for {filename}")
            temporary.replace(archive)
        finally:
            temporary.unlink(missing_ok=True)
    # Copy just the regular executable: do not extract arbitrary paths/links.
    executable = work / member
    with tarfile.open(archive) as source:
        entry = source.getmember(member)
        if not entry.isfile():
            raise RuntimeError(f"7-Zip executable is not a regular file: {member}")
        with source.extractfile(entry) as content, executable.open("wb") as output:
            shutil.copyfileobj(content, output)
    executable.chmod(0o755)
    return str(executable.resolve())
