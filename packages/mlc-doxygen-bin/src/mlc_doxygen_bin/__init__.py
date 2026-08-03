from __future__ import annotations

import json
import platform
from pathlib import Path
from typing import Any

from ._version import DOXYGEN_TAG, __version__

__all__ = [
    "__version__",
    "DOXYGEN_TAG",
    "get_bin_dir",
    "get_executable_path",
    "metadata",
]


def _package_dir() -> Path:
    return Path(__file__).resolve().parent


def get_bin_dir() -> str:
    path = _package_dir() / "bin"
    if not path.is_dir():
        raise FileNotFoundError(f"Doxygen bin directory is missing: {path}")
    return str(path)


def get_executable_path() -> str:
    name = "doxygen.exe" if platform.system() == "Windows" else "doxygen"
    path = Path(get_bin_dir()) / name
    if not path.is_file():
        raise FileNotFoundError(f"Doxygen executable is missing: {path}")
    return str(path)


def metadata() -> dict[str, Any]:
    path = _package_dir() / "doxygen.json"
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))
