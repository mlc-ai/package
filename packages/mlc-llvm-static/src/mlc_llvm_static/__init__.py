"""Locate the installed LLVM development SDK; importing never downloads files."""
from __future__ import annotations

import os
import sysconfig
from importlib.metadata import distribution
from pathlib import Path
from typing import Any

from ._version import LLVM_VERSION, __version__

__all__ = [
    "LLVM_VERSION", "__version__", "get_prefix", "get_cmake_prefix_path",
    "get_cmake_dir", "get_include_dir", "get_library_dir", "get_llvm_config", "metadata",
]


def _require(relative: str, *, executable: bool = False) -> str:
    path = Path(__file__).resolve().parent / relative
    if not path.exists():
        raise FileNotFoundError(f"LLVM SDK artifact is missing: {path}")
    if executable and not os.access(path, os.X_OK):
        raise PermissionError(f"LLVM SDK executable is not executable: {path}")
    return str(path)


def get_prefix() -> str:
    return _require("static")


def get_cmake_prefix_path() -> str:
    return get_prefix()


def get_cmake_dir() -> str:
    return _require("static/lib/cmake/llvm")


def get_include_dir() -> str:
    return _require("static/include")


def get_library_dir() -> str:
    return _require("static/lib")


def get_llvm_config() -> str:
    if os.name == "nt":
        return _windows_launcher()
    return _require("static/bin/llvm-config", executable=True)


def _windows_launcher() -> str:
    # RECORD knows the actual installation scheme, including pip --user.
    # Looking only in sysconfig's default Scripts directory misses user installs;
    # searching PATH could accidentally return a different LLVM distribution.
    installed = distribution("mlc-llvm-static")
    for record in installed.files or []:
        if record.name.lower() == "llvm-config.exe":
            path = Path(installed.locate_file(record)).resolve()
            if path.is_file():
                return str(path)
    path = Path(sysconfig.get_path("scripts")) / "llvm-config.exe"
    if not path.is_file():
        raise FileNotFoundError(f"The pip-installed llvm-config launcher is missing: {path}")
    return str(path)


def metadata(profile: str | None = None) -> dict[str, Any]:
    from ._llvm_config import Configuration

    config = Configuration(Path(get_prefix()), profile)
    result = dict(config.base)
    result["files"] = dict(result["files"])
    if config.profile == "all":
        result["files"].update(config.extra["files"])
    result["targets"] = config.targets
    result["profile"] = config.profile
    result["archive_count"] = sum(name.endswith((".a", ".lib")) for name in result["files"])
    return result
